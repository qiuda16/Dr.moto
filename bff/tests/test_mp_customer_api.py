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
from app.core.db import Base, engine, SessionLocal
from app.routers import customer_app
from app.models import (
    PartCatalogItem,
    PartCatalogProfile,
    VehicleCatalogModel,
    VehicleServicePackage,
    VehicleServicePackageItem,
    VehicleServiceTemplateItem,
    VehicleServiceTemplateProfile,
)


client = TestClient(app)
Base.metadata.create_all(bind=engine)


class FakeRedis:
    def __init__(self):
        self.store = {}

    def setex(self, key, _ttl, value):
        self.store[key] = value

    def get(self, key):
        value = self.store.get(key)
        if value is None:
            return None
        if isinstance(value, bytes):
            return value
        return str(value).encode("utf-8")

    def delete(self, key):
        self.store.pop(key, None)

    def exists(self, key):
        return 1 if key in self.store else 0


class FakeOdoo:
    def __init__(self):
        self.partner = {"id": 101, "name": "Alice Rider", "phone": "13800138000"}
        self.vehicle = {
            "id": 201,
            "partner_id": [101, "Alice Rider"],
            "license_plate": "沪A12345",
            "vin": "VINTEST001",
            "vehicle_id": [301, "Yamaha NMAX 2023"],
        }
        self.model = {"id": 301, "make": "Yamaha", "model": "NMAX", "year_from": 2023, "engine_code": "E-155"}
        self.order = {
            "id": 401,
            "name": "WO-401",
            "vehicle_plate": "沪A12345",
            "state": "done",
            "date_planned": "2026-03-30 10:00:00",
            "amount_total": 199.0,
            "create_date": "2026-03-30 09:00:00",
            "bff_uuid": "wo-uuid-401",
            "description": "Oil change",
            "customer_id": 101,
        }
        self.lines = [
            {
                "id": 501,
                "name": "Engine Oil",
                "quantity": 1,
                "price_unit": 120.0,
                "price_subtotal": 120.0,
                "product_id": [9001, "Oil"],
            }
        ]

    def execute_kw(self, model, method, args, kwargs=None):
        kwargs = kwargs or {}
        if model == "res.partner" and method == "search_read":
            domain = args[0] if args else []
            if ["phone", "=", self.partner["phone"]] in domain:
                return [self.partner]
            if ["id", "=", self.partner["id"]] in domain:
                return [self.partner]
            return []

        if model == "drmoto.partner.vehicle" and method == "search_read":
            domain = args[0] if args else []
            has_partner = ["partner_id", "=", self.partner["id"]] in domain
            has_plate = ["license_plate", "=", self.vehicle["license_plate"]] in domain
            if has_partner and (has_plate or all(item[0] != "license_plate" for item in domain)):
                return [self.vehicle]
            return []

        if model == "drmoto.vehicle" and method == "read":
            ids = args[0] if args else []
            return [self.model] if self.model["id"] in ids else []

        if model == "drmoto.work.order" and method == "search_count":
            return 1

        if model == "drmoto.work.order" and method == "search_read":
            domain = args[0] if args else []
            if ["id", "=", self.order["id"]] in domain and ["customer_id", "=", self.partner["id"]] in domain:
                return [self.order]
            if ["customer_id", "=", self.partner["id"]] in domain and ["vehicle_plate", "=", self.order["vehicle_plate"]] in domain:
                return [self.order]
            return []

        if model == "drmoto.work.order.line" and method == "search_read":
            return self.lines

        return []


def _setup_fakes(monkeypatch):
    monkeypatch.setattr(customer_app, "redis_client", FakeRedis())
    monkeypatch.setattr(customer_app, "odoo_client", FakeOdoo())
    monkeypatch.setattr(
        customer_app,
        "_fetch_wechat_session",
        lambda code: {"openid": f"openid_{code}", "unionid": f"union_{code}"},
    )


def _seed_shop_catalog():
    db = SessionLocal()
    try:
        model = db.query(VehicleCatalogModel).filter(VehicleCatalogModel.brand == "Yamaha", VehicleCatalogModel.model_name == "NMAX").first()
        if model is None:
            model = VehicleCatalogModel(
                brand="Yamaha",
                model_name="NMAX",
                year_from=2020,
                year_to=2025,
                displacement_cc=155,
                category="踏板",
                default_engine_code="E-155",
                is_active=True,
            )
            db.add(model)
            db.flush()

        service = db.query(VehicleServiceTemplateItem).filter(
            VehicleServiceTemplateItem.model_id == model.id,
            VehicleServiceTemplateItem.part_name == "基础保养套餐",
        ).first()
        if service is None:
            service = VehicleServiceTemplateItem(
                model_id=model.id,
                part_name="基础保养套餐",
                part_code="PKG-BASE-001",
                repair_method="更换机油，并检查链条、胎压和刹车状态。",
                labor_hours=0.8,
                notes="测试套餐",
                sort_order=10,
                is_active=True,
            )
            db.add(service)
            db.flush()
            db.add(VehicleServiceTemplateProfile(template_item_id=service.id, labor_price=80.0, suggested_price=198.0))

        part = db.query(PartCatalogItem).filter(PartCatalogItem.part_no == "YAM-OIL-001").first()
        if part is None:
            part = PartCatalogItem(
                part_no="YAM-OIL-001",
                name="Yamaha 10W-40 机油",
                brand="Yamaha",
                category="油液",
                unit="瓶",
                compatible_model_ids=[model.id],
                min_stock=2,
                is_active=True,
            )
            db.add(part)
            db.flush()
            db.add(PartCatalogProfile(part_id=part.id, sale_price=128.0, cost_price=86.0, stock_qty=12.0, supplier_name="测试供应商"))

        package = db.query(VehicleServicePackage).filter(VehicleServicePackage.model_id == model.id, VehicleServicePackage.package_code == "PKG-YAM-BASIC").first()
        if package is None:
            package = VehicleServicePackage(
                model_id=model.id,
                package_code="PKG-YAM-BASIC",
                package_name="Yamaha 基础保养套餐",
                description="测试用保养套餐",
                recommended_interval_km=3000,
                recommended_interval_months=6,
                suggested_price_total=288.0,
                sort_order=10,
                is_active=True,
            )
            db.add(package)
            db.flush()
            db.add(VehicleServicePackageItem(package_id=package.id, template_item_id=service.id, sort_order=10, is_optional=False))

        db.commit()
    finally:
        db.close()


def _bind_and_login(monkeypatch):
    _setup_fakes(monkeypatch)
    _seed_shop_catalog()
    login_resp = client.post("/mp/customer/auth/wechat-login", json={"code": f"code-{uuid.uuid4().hex[:8]}", "store_id": "default"})
    assert login_resp.status_code == 200
    assert login_resp.json()["bound"] is False
    bind_ticket = login_resp.json()["bind_ticket"]

    bind_resp = client.post(
        "/mp/customer/auth/bind",
        json={
            "bind_ticket": bind_ticket,
            "phone": "13800138000",
            "plate_no": "沪A12345",
            "verify_code": "123456",
        },
    )
    assert bind_resp.status_code == 200
    body = bind_resp.json()
    assert body["bound"] is True
    assert body["partner_id"] == 101
    return body


def test_customer_auth_bind_refresh_logout(monkeypatch):
    auth_payload = _bind_and_login(monkeypatch)
    headers = {"Authorization": f"Bearer {auth_payload['access_token']}"}

    me = client.get("/mp/customer/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["partner_id"] == 101

    refresh = client.post("/mp/customer/auth/refresh", json={"refresh_token": auth_payload["refresh_token"]})
    assert refresh.status_code == 200
    new_access_token = refresh.json()["access_token"]
    assert isinstance(new_access_token, str) and len(new_access_token) > 20

    me2 = client.get("/mp/customer/me", headers={"Authorization": f"Bearer {new_access_token}"})
    assert me2.status_code == 200
    assert me2.json()["partner_id"] == 101

    logout = client.post("/mp/customer/auth/logout", headers={"Authorization": f"Bearer {new_access_token}"})
    assert logout.status_code == 200

    me_after_logout = client.get("/mp/customer/me", headers={"Authorization": f"Bearer {new_access_token}"})
    assert me_after_logout.status_code == 401


def test_customer_vehicle_and_order_scope(monkeypatch):
    auth_payload = _bind_and_login(monkeypatch)
    headers = {"Authorization": f"Bearer {auth_payload['access_token']}"}

    vehicles = client.get("/mp/customer/vehicles", headers=headers)
    assert vehicles.status_code == 200
    rows = vehicles.json()
    assert len(rows) == 1
    vehicle_id = rows[0]["id"]
    assert rows[0]["license_plate"] == "沪A12345"

    home = client.get(f"/mp/customer/home?vehicle_id={vehicle_id}", headers=headers)
    assert home.status_code == 200
    assert "pending_recommendations" in home.json()

    health = client.get(f"/mp/customer/vehicles/{vehicle_id}/health-records?limit=10", headers=headers)
    assert health.status_code == 200
    assert isinstance(health.json(), list)

    orders = client.get(f"/mp/customer/vehicles/{vehicle_id}/maintenance-orders?page=1&size=10", headers=headers)
    assert orders.status_code == 200
    assert orders.json()["total"] >= 1

    detail = client.get("/mp/customer/maintenance-orders/401", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["id"] == 401
    assert len(detail.json()["lines"]) == 1

    forbidden_vehicle = client.get("/mp/customer/vehicles/9999/health-records", headers=headers)
    assert forbidden_vehicle.status_code == 404


def test_customer_cockpit_summary(monkeypatch):
    auth_payload = _bind_and_login(monkeypatch)
    headers = {"Authorization": f"Bearer {auth_payload['access_token']}"}

    cockpit = client.get("/mp/customer/cockpit", headers=headers)
    assert cockpit.status_code == 200
    body = cockpit.json()
    assert body["selected_vehicle_id"] == 201
    assert body["vehicle"]["id"] == 201
    assert "health_state" in body
    assert "health_summary" in body
    assert isinstance(body["health_summary"].get("inspection_items"), list)
    assert len(body["health_summary"].get("inspection_items", [])) >= 8
    assert isinstance(body["recommended_services"], list)
    assert isinstance(body["knowledge_docs"], list)
    assert isinstance(body["shop_items"], list)


def test_customer_ai_and_shop_flow(monkeypatch):
    auth_payload = _bind_and_login(monkeypatch)
    headers = {"Authorization": f"Bearer {auth_payload['access_token']}"}

    class FakeAIResponse:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {
                "response": "建议先做基础保养，并查看套餐价格。",
                "suggested_actions": ["查看推荐保养", "预约保养"],
                "action_cards": [{"label": "预约保养", "action": "create_appointment"}],
                "sources": [{"title": "车况摘要"}],
                "debug": {"provider": "test"},
            }

    def fake_post(url, json=None, timeout=None):
        assert url.endswith("/chat")
        assert json["message"]
        return FakeAIResponse()

    monkeypatch.setattr(customer_app.requests, "post", fake_post)

    ai_context = client.get("/mp/customer/ai/context", headers=headers)
    assert ai_context.status_code == 200
    context_body = ai_context.json()
    assert context_body["health_state"] in {"normal", "notice", "warning", "unknown"}
    assert len(context_body.get("inspection_items", [])) >= 8

    ai_chat = client.post(
        "/mp/customer/ai/chat",
        headers=headers,
        json={"message": "这台车要不要保养？", "vehicle_id": context_body["selected_vehicle_id"]},
    )
    assert ai_chat.status_code == 200
    chat_body = ai_chat.json()
    assert chat_body["response"]
    assert chat_body["vehicle_id"] == context_body["selected_vehicle_id"]
    assert isinstance(chat_body["suggested_actions"], list)

    products = client.get("/mp/customer/shop/products?vehicle_id=201", headers=headers)
    assert products.status_code == 200
    product_body = products.json()
    assert len(product_body["items"]) >= 1

    recommendations = client.get("/mp/customer/shop/recommendations?vehicle_id=201", headers=headers)
    assert recommendations.status_code == 200
    assert len(recommendations.json()["items"]) >= 1

    first_product = product_body["items"][0]
    detail = client.get(f"/mp/customer/shop/products/{first_product['id']}?product_type={first_product['product_type']}", headers=headers)
    assert detail.status_code == 200
    detail_item = detail.json()["item"]
    assert detail_item["id"] == first_product["id"]
    assert "cost_price" not in detail_item.get("payload", {})
    assert "labor_price" not in detail_item.get("payload", {})


def test_customer_appointment_draft_flow(monkeypatch):
    auth_payload = _bind_and_login(monkeypatch)
    headers = {"Authorization": f"Bearer {auth_payload['access_token']}"}

    create_resp = client.post(
        "/mp/customer/appointments/draft",
        headers=headers,
        json={
            "vehicle_id": 201,
            "subject": "申请基础保养预约",
            "service_kind": "maintenance",
            "source": "mini_program",
            "notes": "希望周末安排。",
            "payload": {
                "selected_service": "基础保养套餐",
            },
        },
    )
    assert create_resp.status_code == 200
    body = create_resp.json()
    assert body["id"] > 0
    assert body["status"] == "draft"
    assert body["vehicle_id"] == 201
    assert body["vehicle_plate"] == "沪A12345"
    assert body["payload"]["selected_service"] == "基础保养套餐"

    get_resp = client.get(f"/mp/customer/appointments/draft/{body['id']}", headers=headers)
    assert get_resp.status_code == 200
    fetched = get_resp.json()
    assert fetched["id"] == body["id"]
    assert fetched["subject"] == "申请基础保养预约"


def test_customer_requires_valid_token():
    response = client.get("/mp/customer/vehicles")
    assert response.status_code == 401
