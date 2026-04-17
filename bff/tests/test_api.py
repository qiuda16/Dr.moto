import os
import uuid
import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("ODOO_URL", "http://localhost:8069")
os.environ.setdefault("ODOO_DB", "odoo")
os.environ.setdefault("ODOO_USER", "admin")
os.environ.setdefault("ODOO_PASSWORD", "admin")
os.environ["LOGIN_RATE_LIMIT_MAX_ATTEMPTS"] = "1000"
os.environ["LOGIN_RATE_LIMIT_WINDOW_SECONDS"] = "300"

from app.main import app
from app.core import rate_limit
from app.core.db import Base, SessionLocal, engine
from app.core.config import settings
from app.routers import work_orders as work_orders_router
from app.models import (
    AppSetting,
    PaymentLedger,
    PartCatalogItem,
    VehicleCatalogModel,
    VehicleKnowledgeDocument,
    VehicleServiceTemplateItem,
    VehicleServiceTemplateProfile,
    WorkOrder,
)


class FakeRedis:
    def __init__(self):
        self.store = {}

    def _normalize(self, value):
        if isinstance(value, bytes):
            return value
        return str(value).encode("utf-8")

    def get(self, key):
        return self.store.get(key)

    def setex(self, key, _ttl, value):
        self.store[key] = self._normalize(value)

    def incr(self, key):
        current = self.get(key)
        count = int(current.decode("utf-8")) if current else 0
        count += 1
        self.store[key] = str(count).encode("utf-8")
        return count

    def expire(self, _key, _ttl):
        return True

    def delete(self, *keys):
        for key in keys:
            self.store.pop(key, None)

    def keys(self, pattern):
        if pattern.endswith("*"):
            prefix = pattern[:-1]
            return [key for key in self.store if str(key).startswith(prefix)]
        return [key for key in self.store if key == pattern]

client = TestClient(app)
redis_client = FakeRedis()
rate_limit.redis_client = redis_client
Base.metadata.create_all(bind=engine)


def _clear_login_rate_limit():
    keys = redis_client.keys("ratelimit:login:*")
    if keys:
        redis_client.delete(*keys)


def _admin_headers(store_id: str = "default"):
    _clear_login_rate_limit()
    response = client.post(
        "/auth/token",
        data={"username": "admin", "password": "change_me_now"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}", "X-Store-Id": store_id}

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] in {"ok", "degraded"}


def test_app_settings_get_and_update():
    store_id = f"store-settings-{uuid.uuid4().hex[:8]}"
    headers = _admin_headers(store_id)

    get_resp = client.get("/mp/settings", headers=headers)
    assert get_resp.status_code == 200
    settings_payload = get_resp.json()
    assert settings_payload["store_id"] == store_id
    assert settings_payload["store_name"] == "机车博士"
    assert settings_payload["brand_name"] == "DrMoto"

    update_payload = {
        "store_name": "机车博士旗舰店",
        "brand_name": "DrMoto",
        "sidebar_badge_text": "售后管理",
        "primary_color": "#2B7FFF",
        "default_labor_price": 98,
        "default_delivery_note": "已完成交车说明，请按期复检。",
        "common_complaint_phrases": ["更换机油机滤", "检查刹车与轮胎状态"],
    }
    update_resp = client.put("/mp/settings", headers=headers, json=update_payload)
    assert update_resp.status_code == 200
    updated = update_resp.json()
    assert updated["store_name"] == "机车博士旗舰店"
    assert updated["sidebar_badge_text"] == "售后管理"
    assert updated["primary_color"] == "#2B7FFF"
    assert updated["default_labor_price"] == 98
    assert updated["common_complaint_phrases"] == ["更换机油机滤", "检查刹车与轮胎状态"]


def test_delivery_checklist_defaults_follow_store_settings():
    store_id = f"store-delivery-{uuid.uuid4().hex[:8]}"
    headers = _admin_headers(store_id)
    work_order_id = f"wo-delivery-{uuid.uuid4()}"

    db = SessionLocal()
    try:
        db.add(
            AppSetting(
                store_id=store_id,
                store_name="机车博士",
                brand_name="DrMoto",
                sidebar_badge_text="门店管理",
                primary_color="#409EFF",
                default_labor_price=88,
                default_delivery_note="请按期复检并关注机油液位。",
                common_complaint_phrases_json=["常规保养"],
            )
        )
        db.add(
            WorkOrder(
                uuid=work_order_id,
                store_id=store_id,
                odoo_id=6101,
                customer_id="8",
                vehicle_plate="DEL-001",
                description="delivery test",
                status="ready",
            )
        )
        db.commit()
    finally:
        db.close()

    response = client.get(f"/mp/workorders/{work_order_id}/delivery-checklist", headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["notes"] == "请按期复检并关注机油液位。"
    assert payload["payment_method"] == ""
    assert payload["payment_amount"] is None


def test_seed_baseline_services_uses_store_default_labor_price():
    store_id = f"store-service-{uuid.uuid4().hex[:8]}"
    headers = _admin_headers(store_id)
    model_id = None

    db = SessionLocal()
    try:
        db.add(
            AppSetting(
                store_id=store_id,
                store_name="机车博士",
                brand_name="DrMoto",
                sidebar_badge_text="门店管理",
                primary_color="#409EFF",
                default_labor_price=123,
                default_delivery_note="默认交车备注",
                common_complaint_phrases_json=["检查刹车"],
            )
        )
        model = VehicleCatalogModel(
            brand="TEST",
            model_name=f"MODEL-{uuid.uuid4().hex[:6]}",
            year_from=2024,
            year_to=2024,
            displacement_cc=150,
            category="街车",
            fuel_type="gasoline",
            default_engine_code="TEST150",
            source="test",
            is_active=True,
        )
        db.add(model)
        db.commit()
        db.refresh(model)
        model_id = model.id
    finally:
        db.close()

    response = client.post("/mp/catalog/seed-baseline-services", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["seeded"] is True
    assert body["default_labor_price"] == 123.0

    db = SessionLocal()
    try:
        item = (
            db.query(VehicleServiceTemplateItem)
            .filter(VehicleServiceTemplateItem.model_id == model_id)
            .order_by(VehicleServiceTemplateItem.id.asc())
            .first()
        )
        assert item is not None
        profile = (
            db.query(VehicleServiceTemplateProfile)
            .filter(VehicleServiceTemplateProfile.template_item_id == item.id)
            .first()
        )
        assert profile is not None
        assert float(profile.labor_price or 0) == 123.0
    finally:
        db.close()

def test_auth_login():
    _clear_login_rate_limit()
    response = client.post("/auth/token", data={"username": "admin", "password": "change_me_now"}, headers={"Content-Type": "application/x-www-form-urlencoded"})
    assert response.status_code == 200
    assert "access_token" in response.json()

def test_create_work_order_unauthorized():
    response = client.post(
        "/mp/workorders/",
        json={"customer_id": "Test", "vehicle_plate": "TEST-000", "description": "Test"}
    )
    assert response.status_code == 401
    data = response.json()
    assert data["success"] is False
    assert "trace_id" in data


def test_health_probes():
    live = client.get("/health/live")
    assert live.status_code == 200
    assert live.json()["status"] == "alive"

    ready = client.get("/health/ready")
    assert ready.status_code in {200, 503}


def test_work_order_actions_and_invalid_transition():
    wo_id = f"test-wo-actions-{uuid.uuid4()}"
    db = SessionLocal()
    try:
        wo = WorkOrder(
            uuid=wo_id,
            odoo_id=1001,
            customer_id="1",
            vehicle_plate="TEST-ACT",
            description="test",
            status="draft",
        )
        db.add(wo)
        db.commit()
    finally:
        db.close()

    headers = _admin_headers()
    actions = client.get(f"/mp/workorders/{wo_id}/actions", headers=headers)
    assert actions.status_code == 200
    payload = actions.json()
    assert payload["current_status"] == "draft"
    assert any(a["to_status"] == "confirmed" for a in payload["actions"])

    invalid = client.post(f"/mp/workorders/{wo_id}/status?status=done", headers=headers)
    assert invalid.status_code == 409
    err = invalid.json()
    assert err["success"] is False


def test_quote_version_flow():
    wo_id = f"test-wo-quote-{uuid.uuid4()}"
    db = SessionLocal()
    try:
        wo = WorkOrder(
            uuid=wo_id,
            odoo_id=2001,
            customer_id="1",
            vehicle_plate="TEST-QUOTE",
            description="quote test",
            status="draft",
        )
        db.add(wo)
        db.commit()
    finally:
        db.close()

    headers = _admin_headers()
    create_payload = {
        "items": [
            {"item_type": "part", "code": "P-001", "name": "Brake Pad", "qty": 2, "unit_price": 120},
            {"item_type": "service", "code": "L-001", "name": "Labor", "qty": 1, "unit_price": 180},
        ],
        "note": "initial quote"
    }
    v1 = client.post(f"/mp/quotes/{wo_id}/versions", headers=headers, json=create_payload)
    assert v1.status_code == 200
    data = v1.json()
    assert data["version"] == 1
    assert data["status"] == "draft"

    publish = client.post(f"/mp/quotes/{wo_id}/1/publish", headers=headers)
    assert publish.status_code == 200
    assert publish.json()["status"] == "published"
    assert publish.json()["is_active"] is True

    confirm = client.post(f"/mp/quotes/{wo_id}/1/confirm", headers=headers)
    assert confirm.status_code == 200
    assert confirm.json()["status"] == "confirmed"


def test_work_order_page_and_bulk_status():
    headers = _admin_headers()

    wo_filter_id = f"test-wo-filter-{uuid.uuid4()}"
    wo_bulk_id = f"test-wo-bulk-{uuid.uuid4()}"
    db = SessionLocal()
    try:
        db.add(WorkOrder(uuid=wo_filter_id, odoo_id=3001, customer_id="2", vehicle_plate="PAGE001", description="page", status="confirmed"))
        db.add(WorkOrder(uuid=wo_bulk_id, odoo_id=None, customer_id="3", vehicle_plate="BULK001", description="bulk", status="draft"))
        db.commit()
    finally:
        db.close()

    page = client.get("/mp/workorders/list/page?status=confirmed&page=1&size=20", headers=headers)
    assert page.status_code == 200
    data = page.json()
    assert data["page"] == 1
    assert any(item["id"] == wo_filter_id for item in data["items"])

    bulk_payload = {
        "order_ids": [wo_bulk_id],
        "target_status": "confirmed",
        "strict": True
    }
    bulk = client.post("/mp/workorders/bulk/update-status", headers=headers, json=bulk_payload)
    assert bulk.status_code == 200
    bulk_data = bulk.json()
    assert bulk_data["requested"] == 1
    assert bulk_data["succeeded"] == 1
    assert bulk_data["failed"] == 0


def test_resolve_work_order_vehicle_key_prefers_catalog_model(monkeypatch):
    db = SessionLocal()
    try:
        suffix = uuid.uuid4().hex[:6].upper()
        catalog = VehicleCatalogModel(
            brand=f"TEST-BRAND-{suffix}",
            model_name=f"TEST-MODEL-{suffix}",
            year_from=2020,
            year_to=2026,
            displacement_cc=150,
            category="street",
            fuel_type="gasoline",
            default_engine_code=f"ENG-{suffix}",
            source="test",
            is_active=True,
        )
        db.add(catalog)
        db.commit()
        db.refresh(catalog)

        class FakeOdoo:
            def execute_kw(self, model, method, args, kwargs=None):
                kwargs = kwargs or {}
                if model == "drmoto.partner.vehicle" and method == "search_read":
                    return [{"id": 1, "partner_id": [88, "Test"], "license_plate": "TEST888", "vehicle_id": [501, f"{catalog.brand} {catalog.model_name}"]}]
                if model == "drmoto.vehicle" and method == "read":
                    return [{"id": 501, "make": catalog.brand, "model": catalog.model_name, "year_from": 2024, "engine_code": catalog.default_engine_code}]
                raise AssertionError(f"Unexpected Odoo call: {model}.{method}")

        monkeypatch.setattr(work_orders_router, "odoo_client", FakeOdoo())
        key = work_orders_router._resolve_work_order_vehicle_key(db, 88, "TEST888")
        assert key == f"CATALOG_MODEL:{catalog.id}"
    finally:
        db.close()


def test_store_scope_isolation():
    same_plate = f"TEST-SCOPE-{uuid.uuid4().hex[:6]}"
    wo_a = f"test-wo-store-a-{uuid.uuid4()}"
    wo_b = f"test-wo-store-b-{uuid.uuid4()}"

    db = SessionLocal()
    try:
        db.add(WorkOrder(uuid=wo_a, store_id="store-a", odoo_id=4001, customer_id="4", vehicle_plate=same_plate, description="a", status="draft"))
        db.add(WorkOrder(uuid=wo_b, store_id="store-b", odoo_id=4002, customer_id="5", vehicle_plate=same_plate, description="b", status="draft"))
        db.commit()
    finally:
        db.close()

    headers_a = _admin_headers("store-a")
    headers_b = _admin_headers("store-b")

    resp_a = client.get(f"/mp/workorders/search?plate={same_plate}", headers=headers_a)
    assert resp_a.status_code == 200
    ids_a = [item["id"] for item in resp_a.json()]
    assert wo_a in ids_a
    assert wo_b not in ids_a

    resp_b = client.get(f"/mp/workorders/search?plate={same_plate}", headers=headers_b)
    assert resp_b.status_code == 200
    ids_b = [item["id"] for item in resp_b.json()]
    assert wo_b in ids_b
    assert wo_a not in ids_b


def test_payment_webhook_store_scoped():
    wo_id = f"test-wo-pay-{uuid.uuid4()}"
    tx = f"PAYTEST-{uuid.uuid4().hex[:8]}"

    db = SessionLocal()
    try:
        db.add(WorkOrder(uuid=wo_id, store_id="store-a", odoo_id=5001, customer_id="6", vehicle_plate="PAYA01", description="pay", status="draft"))
        db.add(PaymentLedger(transaction_id=tx, store_id="store-a", work_order_id=wo_id, amount=99.0, status="pending", provider="mock"))
        db.commit()
    finally:
        db.close()

    payload = {"payment_id": "cb-1", "status": "paid", "transaction_id": tx}
    resp_ok = client.post("/mp/payments/webhook/mock", json=payload, headers={"X-Store-Id": "store-a"})
    assert resp_ok.status_code == 200
    assert resp_ok.json()["status"] == "accepted"
    assert resp_ok.json()["ledger_status"] == "success"

    resp_ignored = client.post("/mp/payments/webhook/mock", json=payload, headers={"X-Store-Id": "store-b"})
    assert resp_ignored.status_code == 200
    assert resp_ignored.json()["status"] == "ignored"


def test_wechat_intent_requires_configuration():
    headers = _admin_headers("store-a")
    create_customer = client.post(
        "/mp/workorders/customers",
        headers=headers,
        json={"name": "Pay User", "phone": "13800000001", "email": "pay@example.com"},
    )
    assert create_customer.status_code == 200
    customer_id = create_customer.json()["id"]

    create_wo = client.post(
        "/mp/workorders/",
        headers=headers,
        json={"customer_id": str(customer_id), "vehicle_plate": f"WX{uuid.uuid4().hex[:6]}", "description": "wechat intent test"},
    )
    assert create_wo.status_code == 200
    wo_id = create_wo.json()["id"]

    intent_resp = client.post(
        "/mp/payments/create_intent",
        headers=headers,
        json={"work_order_id": wo_id, "amount": 10.5, "provider": "wechat"},
    )
    assert intent_resp.status_code == 501


def test_customer_create_with_vehicle_and_query():
    headers = _admin_headers("store-a")
    plate = f"CUST{uuid.uuid4().hex[:6]}".upper()
    payload = {
        "name": f"客户{uuid.uuid4().hex[:4]}",
        "phone": "13900001111",
        "email": "owner@example.com",
        "vehicles": [
            {
                "license_plate": plate,
                "make": "Yamaha",
                "model": "NMAX",
                "year": 2023,
                "engine_code": "E-155",
                "vin": f"VIN{uuid.uuid4().hex[:10]}",
                "color": "Black",
            }
        ],
    }
    create_resp = client.post("/mp/workorders/customers", headers=headers, json=payload)
    assert create_resp.status_code == 200
    body = create_resp.json()
    assert body["id"] > 0
    assert body["vehicle_count"] >= 1

    list_resp = client.get("/mp/workorders/customers/with-vehicles", headers=headers, params={"query": payload["name"], "limit": 20})
    assert list_resp.status_code == 200
    rows = list_resp.json()
    assert any(item["id"] == body["id"] for item in rows)


def test_customer_summary_endpoint():
    headers = _admin_headers("store-a")
    payload = {
        "name": f"Customer{uuid.uuid4().hex[:4]}",
        "phone": "13900002222",
        "vehicles": [
            {
                "license_plate": f"SUM{uuid.uuid4().hex[:6]}".upper(),
                "make": "Toyota",
                "model": "Corolla",
                "year": 2022,
            }
        ],
    }
    create_resp = client.post("/mp/workorders/customers", headers=headers, json=payload)
    assert create_resp.status_code == 200
    customer_id = create_resp.json()["id"]

    summary_resp = client.get(f"/mp/workorders/customers/{customer_id}/summary", headers=headers)
    assert summary_resp.status_code == 200
    summary = summary_resp.json()
    assert summary["customer_id"] == customer_id
    assert "total_orders" in summary


def test_customer_with_vehicle_search_prioritizes_exact_name():
    headers = _admin_headers("store-a")
    exact_name = f"客户{uuid.uuid4().hex[:4]}"
    fuzzy_name = f"{exact_name} 测试"
    exact_plate = f"EX{uuid.uuid4().hex[:6]}".upper()
    fuzzy_plate = f"FU{uuid.uuid4().hex[:6]}".upper()

    exact_resp = client.post(
        "/mp/workorders/customers",
        headers=headers,
        json={
            "name": exact_name,
            "phone": "13900003333",
            "vehicles": [{"license_plate": exact_plate, "make": "Suzuki", "model": "GSX150F", "year": 2025}],
        },
    )
    assert exact_resp.status_code == 200

    fuzzy_resp = client.post(
        "/mp/workorders/customers",
        headers=headers,
        json={
            "name": fuzzy_name,
            "phone": "13900004444",
            "vehicles": [{"license_plate": fuzzy_plate, "make": "Suzuki", "model": "GSX150F", "year": 2025}],
        },
    )
    assert fuzzy_resp.status_code == 200

    list_resp = client.get("/mp/workorders/customers/with-vehicles", headers=headers, params={"query": exact_name, "limit": 20})
    assert list_resp.status_code == 200
    rows = list_resp.json()
    assert rows
    assert rows[0]["name"] == exact_name


def test_catalog_part_search_prioritizes_exact_part_no():
    headers = _admin_headers("store-a")
    exact_no = f"FILTER-{uuid.uuid4().hex[:6].upper()}"
    fuzzy_no = f"X-{exact_no}"
    db = SessionLocal()
    try:
        db.add(PartCatalogItem(part_no=fuzzy_no, name="Filter Backup", brand="DrMoto", category="保养", unit="件", is_active=True))
        db.add(PartCatalogItem(part_no=exact_no, name="Filter Exact", brand="DrMoto", category="保养", unit="件", is_active=True))
        db.commit()
    finally:
        db.close()

    resp = client.get("/mp/catalog/parts", headers=headers, params={"keyword": exact_no, "page": 1, "size": 10})
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert items
    assert items[0]["part_no"] == exact_no


def test_catalog_vehicle_search_prioritizes_exact_model_name():
    headers = _admin_headers("store-a")
    brand = f"TestBrand{uuid.uuid4().hex[:4]}"
    exact_model = f"Model {uuid.uuid4().hex[:4].upper()}"
    fuzzy_model = f"{exact_model} Touring"
    db = SessionLocal()
    try:
        db.add(VehicleCatalogModel(brand=brand, model_name=fuzzy_model, year_from=2024, year_to=2026, category="踏板", is_active=True))
        db.add(VehicleCatalogModel(brand=brand, model_name=exact_model, year_from=2025, year_to=2026, category="踏板", is_active=True))
        db.commit()
    finally:
        db.close()

    resp = client.get("/mp/catalog/vehicle-models", headers=headers, params={"keyword": exact_model, "page": 1, "size": 10})
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert items
    assert items[0]["model_name"] == exact_model


def test_knowledge_document_search_prioritizes_exact_title():
    headers = _admin_headers("store-a")
    title = f"GSX150F 机油滤芯"
    db = SessionLocal()
    try:
        model = VehicleCatalogModel(brand="Suzuki", model_name=f"GSX150F TEST {uuid.uuid4().hex[:4]}", year_from=2025, year_to=2026, category="街车", is_active=True)
        db.add(model)
        db.flush()
        db.add(VehicleKnowledgeDocument(model_id=model.id, title=f"{title} 拆装说明", file_name="doc-fuzzy.pdf", file_url="http://example.com/fuzzy.pdf", category="维修手册"))
        db.add(VehicleKnowledgeDocument(model_id=model.id, title=title, file_name="doc-exact.pdf", file_url="http://example.com/exact.pdf", category="维修手册"))
        db.commit()
    finally:
        db.close()

    resp = client.get("/mp/knowledge/documents", headers=headers, params={"keyword": title})
    assert resp.status_code == 200
    items = resp.json()
    assert items
    assert items[0]["title"] == title
