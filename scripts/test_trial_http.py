"""Create disposable trial records in an explicitly selected development BFF."""

import argparse
import json
import os
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError
import uuid


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    args = parser.parse_args()
    base = args.base_url.rstrip("/")
    token = None

    def call(path, payload=None, form=False, method=None):
        headers = {"X-Store-Id": "default"}
        if token:
            headers["Authorization"] = "Bearer " + token
        body = None
        if payload is not None:
            body = (urlencode(payload) if form else json.dumps(payload)).encode()
            headers["Content-Type"] = "application/x-www-form-urlencoded" if form else "application/json"
        with urlopen(Request(base + path, data=body, headers=headers, method=method), timeout=20) as response:
            return json.load(response)

    health = call("/health")
    assert health["env"] == "dev", "Use only an isolated development BFF"
    assert health["db"] == "ok" and health["odoo"] == "ok"
    token = call("/auth/token", {"username": os.getenv("TRIAL_TEST_USERNAME", "admin"),
        "password": os.getenv("TRIAL_TEST_PASSWORD", "change_me_now")}, form=True)["access_token"]
    paid_before = call("/mp/dashboard/summary")["payments"]["paid_amount_total"]
    suffix = uuid.uuid4().hex[:8].upper()
    phone = "139" + str(int(suffix, 16) % 100000000).zfill(8)
    plate = "TEST" + suffix
    customer = call("/mp/workorders/customers", {
        "name": "Integration " + suffix, "phone": phone,
        "vehicles": [{"license_plate": plate, "make": "Yamaha", "model": "NMAX", "year": 2023}]})
    assert customer["id"] > 0 and customer["vehicle_count"] >= 1
    lead = call("/mp/leads", {"name": "Integration " + suffix,
        "contact": phone, "message": "HTTP acceptance", "source_page": "integration"})["lead"]
    assert any(row["source_type"] == "lead" and row["id"] == lead["id"]
               for row in call("/mp/trial/inbox"))
    conversion = {"source_type": "lead", "source_id": lead["id"],
        "customer_id": str(customer["id"]), "vehicle_plate": plate, "description": "HTTP acceptance"}
    order = call("/mp/trial/workorders", conversion)
    try:
        call("/mp/trial/workorders", conversion)
    except HTTPError as exc:
        assert exc.code == 409
    else:
        raise AssertionError("Duplicate conversion was accepted")
    order_path = "/mp/workorders/" + order["id"]
    for state in ["confirmed", "diagnosing"]:
        assert call(order_path + "/status?status=" + state, {})["new_state"] == state
    record = call(order_path + "/process-record",
                  {"symptom_confirmed": "Customer complaint verified"}, method="PUT")
    assert record["symptom_confirmed"] == "Customer complaint verified"
    quote_path = "/mp/quotes/" + order["id"]
    quote = call(quote_path + "/versions", {"items": [
        {"name": "Inspection", "qty": 1, "unit_price": 199.0}]})
    version_path = quote_path + "/" + str(quote["version"])
    assert call(version_path + "/publish", {})["status"] == "published"
    confirmed = call(version_path + "/confirm", {})
    assert confirmed["status"] == "confirmed" and confirmed["amount_total"] == 199.0
    try:
        call(order_path + "/status?status=quoted", {})
    except HTTPError as exc:
        assert exc.code == 409
    else:
        raise AssertionError("Order without service selection advanced to quoted")
    model = call("/mp/catalog/vehicle-models", {"brand": "Integration",
        "model_name": suffix, "year_from": 2023})
    service = call("/mp/catalog/vehicle-models/" + str(model["id"]) + "/service-items", {
        "service_name": "Inspection", "service_code": suffix,
        "repair_method": "Inspect and verify vehicle", "labor_hours": 1,
        "suggested_price": 199.0})
    call(order_path + "/service-selections", {"template_item_id": service["id"]})
    for state in ["quoted", "in_progress"]:
        assert call(order_path + "/status?status=" + state, {})["new_state"] == state
    health_path = "/mp/workorders/customers/" + str(customer["id"]) + "/vehicles/" + plate + "/health-records"
    health_record = call(health_path, {"odometer_km": 12000,
        "battery_voltage": 12.8, "notes": "Completion inspection"})
    assert health_record["vehicle_plate"] == plate
    assert call(order_path + "/status?status=ready", {})["new_state"] == "ready"
    payment_path = "/mp/workorders/" + order["id"] + "/offline-payment"
    payment_data = {"amount": 199.0, "payment_method": "cash", "idempotency_key": suffix}
    payment = call(payment_path, payment_data)
    assert call(payment_path, payment_data)["id"] == payment["id"]
    payments = call("/mp/workorders/" + order["id"] + "/offline-payments")
    assert len(payments) == 1 and payments[0]["amount"] == 199.0
    call(order_path + "/delivery-checklist", {"explained_to_customer": True,
        "payment_confirmed": True, "payment_method": "cash", "payment_amount": 199.0}, method="PUT")
    assert call(order_path + "/status?status=done", {})["new_state"] == "done"
    assert call(order_path)["status"] == "done"
    summary = call("/mp/dashboard/summary")
    assert round(summary["payments"]["paid_amount_total"] - paid_before, 2) == 199.0
    overview = call("/mp/dashboard/overview")
    assert overview["payments"]["paid_amount_total"] == summary["payments"]["paid_amount_total"]
    assert any(row["work_order_id"] == order["id"] and row["amount"] == 199.0
               for row in overview["recent"]["payments"])
    login = call("/mp/customer/auth/wechat-login", {"code": "integration-" + suffix, "store_id": "default"})
    bound = call("/mp/customer/auth/bind", {"bind_ticket": login["bind_ticket"],
        "phone": phone, "plate_no": plate, "verify_code": "123456"})
    assert bound["partner_id"] == customer["id"]
    token = bound["access_token"]
    vehicles = call("/mp/customer/vehicles")
    rows = vehicles if isinstance(vehicles, list) else vehicles["items"]
    vehicle = next(row for row in rows if row["license_plate"] == plate)
    history = call("/mp/customer/vehicles/" + str(vehicle["id"]) + "/maintenance-orders")
    completed = next(row for row in history["items"] if row["bff_uuid"] == order["id"])
    assert completed["state"] == "done"
    assert completed["payment_summary"]["status"] == "paid"
    assert completed["payment_summary"]["paid_amount"] == 199.0
    assert completed["amount_total"] == 199.0, "Customer history amount differs from confirmed quote"
    detail = call("/mp/customer/maintenance-orders/" + str(completed["id"]))
    assert detail["amount_total"] == 199.0
    assert detail["quote_summary"]["status"] == "confirmed"
    assert sum(line["price_subtotal"] for line in detail["lines"]) == 199.0
    print("PASS: real HTTP customer/vehicle, lead/inbox, conversion, diagnosis, quote, construction, health check, payment, delivery and retries")
    print("Order:", order["id"])
    print("PASS: customer binding, vehicle list and completed paid order history (development WeChat identity)")


if __name__ == "__main__":
    main()
