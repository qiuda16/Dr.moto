import os
import uuid
from datetime import datetime, timezone

from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("ODOO_URL", "http://localhost:8069")
os.environ.setdefault("ODOO_DB", "odoo")
os.environ.setdefault("ODOO_USER", "admin")
os.environ.setdefault("ODOO_PASSWORD", "admin")
os.environ.setdefault("LOGIN_RATE_LIMIT_MAX_ATTEMPTS", "1000")
os.environ.setdefault("LOGIN_RATE_LIMIT_WINDOW_SECONDS", "300")

from app.main import app
from app.core.db import Base, engine
from app.routers import customer_app


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


def _bind_and_login(monkeypatch):
    _setup_fakes(monkeypatch)
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


def test_customer_requires_valid_token():
    response = client.get("/mp/customer/vehicles")
    assert response.status_code == 401
