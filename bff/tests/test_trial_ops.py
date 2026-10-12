import os

from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("ODOO_URL", "http://localhost:8069")
os.environ.setdefault("ODOO_DB", "odoo")
os.environ.setdefault("ODOO_USER", "admin")
os.environ.setdefault("ODOO_PASSWORD", "admin")
os.environ.setdefault("LOGIN_RATE_LIMIT_MAX_ATTEMPTS", "1000")
os.environ.setdefault("LOGIN_RATE_LIMIT_WINDOW_SECONDS", "300")

from app.core.db import Base, engine
from app.core.security import create_access_token
from app.main import app
from app.routers import trial_ops
from app.models import WorkOrderOfflinePayment, CustomerAppointmentDraft


client = TestClient(app)
Base.metadata.create_all(bind=engine)


class FakeOdoo:
    def __init__(self):
        self.next_id = 700
        self.created = []

    def execute_kw(self, model, method, args, kwargs=None):
        if model == "drmoto.work.order" and method == "create":
            self.next_id += 1
            payload = args[0]
            self.created.append(payload)
            return self.next_id
        return []


def _staff_headers():
    token = create_access_token({"sub": "trial-admin", "role": "admin", "email": "trial-admin@drmoto.local"})
    return {"Authorization": f"Bearer {token}", "X-Store-Id": "default"}


def test_dashboard_includes_offline_receipts_with_store_and_date_scope():
    import uuid
    from datetime import datetime, timezone, timedelta
    from sqlalchemy.orm import Session

    store = "dashboard-" + uuid.uuid4().hex
    now = datetime.now(timezone.utc)
    with Session(bind=engine) as db:
        for store_id, amount, received_at, status in [
            (store, 199, now, "paid"), (store, 50, now - timedelta(days=1), "paid"),
            (store, 100, now, "void"), (store + "-other", 999, now, "paid"),
        ]:
            db.add(WorkOrderOfflinePayment(store_id=store_id, work_order_uuid=uuid.uuid4().hex,
                amount=amount, received_at=received_at, payment_method="cash", status=status))
        db.commit()
    headers = {**_staff_headers(), "X-Store-Id": store}
    summary = client.get("/mp/dashboard/summary", headers=headers)
    assert summary.status_code == 200
    assert summary.json()["payments"]["paid_amount_total"] == 249
    overview = client.get("/mp/dashboard/overview", headers=headers)
    assert overview.status_code == 200
    data = overview.json()
    assert data["payments"]["paid_amount_total"] == 249
    assert data["kpi"]["today_paid_amount"] == 199
    assert data["kpi"]["avg_ticket_amount"] == 124.5
    assert len(data["recent"]["payments"]) == 2


def test_appointment_conversion_cannot_create_duplicate_order(monkeypatch):
    from sqlalchemy.orm import Session
    from datetime import datetime

    fake_odoo = FakeOdoo()
    monkeypatch.setattr(trial_ops, "odoo_client", fake_odoo)
    with Session(bind=engine) as db:
        draft = CustomerAppointmentDraft(store_id="default", partner_id=101,
            vehicle_plate="TEST123", subject="Service appointment", status="submitted",
            preferred_date=datetime(2026, 10, 20, 9, 30), source="mini_program")
        db.add(draft)
        db.commit()
        draft_id = draft.id
    payload = {"source_type": "appointment", "source_id": draft_id}
    first = client.post("/mp/trial/workorders", headers=_staff_headers(), json=payload)
    assert first.status_code == 200
    assert fake_odoo.created[0]["date_planned"] == "2026-10-20 09:30:00"
    assert "Service appointment" in fake_odoo.created[0]["description"]
    assert "mini_program" in fake_odoo.created[0]["description"]
    duplicate = client.post("/mp/trial/workorders", headers=_staff_headers(), json=payload)
    assert duplicate.status_code == 409
    assert len(fake_odoo.created) == 1
    inbox = client.get("/mp/trial/inbox", headers=_staff_headers())
    assert inbox.status_code == 200
    assert not any(row["source_type"] == "appointment" and row["id"] == draft_id
                   for row in inbox.json())


def test_website_lead_inbox_convert_and_offline_payment(monkeypatch):
    fake_odoo = FakeOdoo()
    monkeypatch.setattr(trial_ops, "odoo_client", fake_odoo)

    lead_resp = client.post(
        "/mp/leads",
        json={
            "name": "张先生",
            "contact": "13800138000",
            "identity": "车主",
            "message": "想预约透明检测",
            "source_page": "https://drmoto.cn/contact",
        },
    )
    assert lead_resp.status_code == 200
    lead = lead_resp.json()["lead"]
    assert lead["status"] == "new"

    inbox = client.get("/mp/trial/inbox", headers=_staff_headers())
    assert inbox.status_code == 200
    assert any(item["source_type"] == "lead" and item["id"] == lead["id"] for item in inbox.json())

    contacted = client.put(f"/mp/leads/{lead['id']}", headers=_staff_headers(), json={"status": "contacted"})
    assert contacted.status_code == 200
    assert contacted.json()["status"] == "contacted"

    convert = client.post(
        "/mp/trial/workorders",
        headers=_staff_headers(),
        json={
            "source_type": "lead",
            "source_id": lead["id"],
            "customer_id": "101",
            "vehicle_plate": "沪A12345",
            "description": "官网线索转接车检测",
        },
    )
    assert convert.status_code == 200
    work_order_id = convert.json()["id"]
    assert fake_odoo.created[-1]["customer_id"] == 101
    assert fake_odoo.created[-1]["vehicle_plate"] == "沪A12345"

    payment_key = f"payment-{lead['id']}"
    payment = client.post(
        f"/mp/workorders/{work_order_id}/offline-payment",
        headers=_staff_headers(),
        json={"amount": 199.0, "payment_method": "wechat", "payer_note": "客户已线下转账", "idempotency_key": payment_key},
    )
    assert payment.status_code == 200
    assert payment.json()["status"] == "paid"
    assert payment.json()["amount"] == 199.0

    duplicate_payment = client.post(
        f"/mp/workorders/{work_order_id}/offline-payment",
        headers=_staff_headers(),
        json={"amount": 199.0, "payment_method": "wechat", "idempotency_key": payment_key},
    )
    assert duplicate_payment.status_code == 200
    assert duplicate_payment.json()["id"] == payment.json()["id"]

    duplicate_conversion = client.post(
        "/mp/trial/workorders",
        headers=_staff_headers(),
        json={
            "source_type": "lead",
            "source_id": lead["id"],
            "customer_id": "101",
            "vehicle_plate": "沪A12345",
            "description": "重复提交应被拒绝",
        },
    )
    assert duplicate_conversion.status_code == 409

    from sqlalchemy.orm import Session

    with Session(bind=engine) as db:
        rows = db.query(WorkOrderOfflinePayment).filter(WorkOrderOfflinePayment.work_order_uuid == work_order_id).all()
        assert len(rows) == 1
        assert rows[0].payment_method == "wechat"
