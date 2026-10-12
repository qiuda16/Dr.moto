import os
import uuid

from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("ODOO_URL", "http://localhost:8069")
os.environ.setdefault("ODOO_DB", "odoo")
os.environ.setdefault("ODOO_USER", "admin")
os.environ.setdefault("ODOO_PASSWORD", "admin")
os.environ.setdefault("LOGIN_RATE_LIMIT_MAX_ATTEMPTS", "1000")
os.environ.setdefault("LOGIN_RATE_LIMIT_WINDOW_SECONDS", "300")

from app.main import app
from app.core import rate_limit
from app.core.config import settings
from app.core.db import Base, SessionLocal, engine
from app.models import PartCatalogItem, PartCatalogProfile, VehicleCatalogModel, VehicleServicePackage, VehicleServicePackageItem, VehicleServiceTemplateItem, WorkOrder


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
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}", "X-Store-Id": store_id}


def test_ai_ops_context_and_actions():
    work_order_id = f"ai-ops-wo-{uuid.uuid4()}"
    headers = _admin_headers()

    db = SessionLocal()
    try:
        db.add(
            WorkOrder(
                uuid=work_order_id,
                store_id="default",
                odoo_id=9101,
                customer_id="11",
                vehicle_plate="AI-TEST-01",
                description="customer reported brake noise",
                status="confirmed",
            )
        )
        db.commit()
    finally:
        db.close()

    context = client.get(f"/ai/ops/context?work_order_id={work_order_id}", headers=headers)
    assert context.status_code == 200
    context_payload = context.json()
    assert context_payload["matched_work_order"]["id"] == work_order_id
    assert context_payload["matched_work_order"]["status"] == "confirmed"
    assert "append_work_order_internal_note" in context_payload["write_capabilities"]

    note_resp = client.post(
        "/ai/ops/actions",
        headers=headers,
        json={
            "action": "append_work_order_internal_note",
            "payload": {"work_order_id": work_order_id, "note": "Customer prefers afternoon pickup"},
        },
    )
    assert note_resp.status_code == 200
    assert "afternoon pickup" in note_resp.json()["result"]["internal_notes"]

    quote_resp = client.post(
        "/ai/ops/actions",
        headers=headers,
        json={
            "action": "create_quote_draft",
            "payload": {
                "work_order_id": work_order_id,
                "items": [
                    {"item_type": "part", "code": "PAD-01", "name": "Brake Pad", "qty": 1, "unit_price": 220},
                    {"item_type": "service", "code": "LAB-01", "name": "Brake Service", "qty": 1, "unit_price": 120},
                ],
                "note": "ai draft",
            },
        },
    )
    assert quote_resp.status_code == 200
    quote_payload = quote_resp.json()["result"]
    assert quote_payload["version"] == 1
    assert quote_payload["amount_total"] == 340.0


def test_ai_ops_context_returns_service_items():
    headers = _admin_headers()
    model_code = f"AI-SVC-MODEL-{uuid.uuid4().hex[:8].upper()}"
    service_name = f"AI单测标准项目-{uuid.uuid4().hex[:8].upper()}"
    repair_method = "拆装火花塞并检查燃烧情况，按规范力矩安装新火花塞，确认点火顺畅。"

    db = SessionLocal()
    try:
        model = VehicleCatalogModel(
            brand="DrMoto",
            model_name="AI 单测车型",
            category="test",
            year_from=2024,
            year_to=2026,
            is_active=True,
        )
        db.add(model)
        db.flush()
        db.add(
            VehicleServiceTemplateItem(
                model_id=model.id,
                part_name=service_name,
                part_code=model_code,
                repair_method=repair_method,
                labor_hours=0.8,
                notes="service item test",
                sort_order=1,
                is_active=True,
            )
        )
        db.commit()
    finally:
        db.close()

    context = client.get(f"/ai/ops/context?query={service_name}", headers=headers)
    assert context.status_code == 200
    context_payload = context.json()
    assert "service_items" in context_payload
    assert context_payload["service_items"]
    assert any(item["service_name"] == service_name for item in context_payload["service_items"])
    match = next(item for item in context_payload["service_items"] if item["service_name"] == service_name)
    assert match["repair_method"] == repair_method
    assert "service_items" in context_payload["query_domains"]
    assert context_payload["primary_domain"] == "service_items"


def test_ai_ops_context_returns_shop_items_and_ai_answers_them():
    headers = _admin_headers()
    service_name = f"AI商城服务-{uuid.uuid4().hex[:8].upper()}"
    package_name = f"AI商城套餐-{uuid.uuid4().hex[:8].upper()}"
    repair_method = "拆装火花塞并检查燃烧情况，按规范力矩安装新火花塞，确认点火顺畅。"

    db = SessionLocal()
    try:
        model = VehicleCatalogModel(
            brand="DrMoto",
            model_name="AI 商城车型",
            category="test",
            year_from=2024,
            year_to=2026,
            is_active=True,
        )
        db.add(model)
        db.flush()
        service_item = VehicleServiceTemplateItem(
            model_id=model.id,
            part_name=service_name,
            part_code=f"SHOP-SVC-{uuid.uuid4().hex[:6].upper()}",
            repair_method=repair_method,
            labor_hours=1.0,
            notes="shop service test",
            sort_order=1,
            is_active=True,
        )
        db.add(service_item)
        db.flush()
        package = VehicleServicePackage(
            model_id=model.id,
            package_name=package_name,
            package_code=f"SHOP-PKG-{uuid.uuid4().hex[:6].upper()}",
            description="AI商城套餐测试",
            suggested_price_total=288.0,
            is_active=True,
            sort_order=1,
        )
        db.add(package)
        db.flush()
        db.add(
            VehicleServicePackageItem(
                package_id=package.id,
                template_item_id=service_item.id,
                sort_order=1,
                is_optional=False,
            )
        )
        db.commit()
    finally:
        db.close()

    context = client.get("/ai/ops/context?query=%E5%95%86%E5%9F%8E", headers=headers)
    assert context.status_code == 200
    context_payload = context.json()
    assert "shop_items" in context_payload
    assert context_payload["shop_items"]
    assert context_payload["primary_domain"] == "shop"

    chat = client.post(
        "/ai/assistant/chat",
        headers=headers,
        json={
            "message": "请直接告诉我商城里有什么商品。",
            "user_id": "ai-test",
            "context": context_payload,
        },
    )
    assert chat.status_code == 200
    response_text = chat.json()["response"]
    assert package_name in response_text or service_name in response_text
    assert "商品" in response_text


def test_shop_browse_without_vehicle_does_not_claim_compatibility():
    from app.routers.ai_ops import _shop_items

    name = "Browse-" + uuid.uuid4().hex
    with SessionLocal() as db:
        model = VehicleCatalogModel(brand="Test", model_name=name, year_from=2024, is_active=True)
        db.add(model)
        db.flush()
        model_id = model.id
        db.add(VehicleServicePackage(model_id=model_id, package_name=name,
            package_code=name, suggested_price_total=199, is_active=True))
        db.commit()
        general = _shop_items(db, None, query=name)
        assert general
        assert general[0]["compatible_model_ids"] == [model_id]
        assert general[0]["is_recommended"] is False
        matching = _shop_items(db, model_id, query=name)
        assert matching[0]["is_recommended"] is True
        assert _shop_items(db, model_id + 1000000, query=name) == []


def test_ai_ops_create_and_update_part():
    headers = _admin_headers()
    part_no = f"AI-PART-{uuid.uuid4().hex[:8].upper()}"

    create_resp = client.post(
        "/ai/ops/actions",
        headers=headers,
        json={
            "action": "create_part",
            "payload": {
                "part_no": part_no,
                "name": "AI Test Part",
                "brand": "DrMoto",
                "category": "Test",
                "unit": "pcs",
                "sale_price": 88,
                "cost_price": 55,
                "stock_qty": 9,
            },
        },
    )
    assert create_resp.status_code == 200
    result = create_resp.json()["result"]
    assert result["part_no"] == part_no
    assert result["sale_price"] == 88.0

    db = SessionLocal()
    try:
        part = db.query(PartCatalogItem).filter(PartCatalogItem.part_no == part_no).first()
        assert part is not None
        profile = db.query(PartCatalogProfile).filter(PartCatalogProfile.part_id == part.id).first()
        assert profile is not None
        part_id = part.id
    finally:
        db.close()

    update_resp = client.post(
        "/ai/ops/actions",
        headers=headers,
        json={
            "action": "update_part",
            "payload": {
                "part_id": part_id,
                "name": "AI Test Part Updated",
                "stock_qty": 12,
                "sale_price": 96,
            },
        },
    )
    assert update_resp.status_code == 200
    updated = update_resp.json()["result"]
    assert updated["name"] == "AI Test Part Updated"
    assert updated["stock_qty"] == 12.0
    assert updated["sale_price"] == 96.0
