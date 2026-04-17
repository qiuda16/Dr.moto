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
from app.models import PartCatalogItem, PartCatalogProfile, WorkOrder


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
