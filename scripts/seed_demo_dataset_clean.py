from dataclasses import dataclass
from typing import Any

import requests


BFF_URL = "http://127.0.0.1:18080"
USERNAME = "admin"
PASSWORD = "change_me_now"
STORE_ID = "default"
TIMEOUT = 20


@dataclass(frozen=True)
class DemoCase:
    customer_name: str
    phone: str
    email: str
    plate: str
    make: str
    model: str
    year: int
    engine_code: str
    color: str
    description: str
    symptom_draft: str
    symptom_confirmed: str
    quick_check: dict[str, Any]
    health_record: dict[str, Any]
    quote_items: list[dict[str, Any]]


CASES = [
    DemoCase(
        customer_name="测试客户A",
        phone="13900001111",
        email="demo.customer.a@drmoto.local",
        plate="TEST1234",
        make="Tesla",
        model="Model Y",
        year=2024,
        engine_code="EV",
        color="White",
        description="前制动偏软，顺便做常规检查",
        symptom_draft="前制动偏软，需要检查刹车油和制动手感",
        symptom_confirmed="确认前制动手感偏软，建议检查刹车油并排空气",
        quick_check={
            "odometer_km": 12850,
            "battery_voltage": 12.6,
            "tire_front_psi": 33,
            "tire_rear_psi": 35,
            "engine_noise_note": "",
            "brake": "前制动手感偏软",
        },
        health_record={
            "measured_at": "2026-03-30T21:08:26+08:00",
            "odometer_km": 12850,
            "battery_voltage": 12.6,
            "oil_life_percent": 46,
            "notes": "演示体检记录，建议复查前制动系统",
            "extra": {
                "brake": "建议复查前制动系统",
                "chain": "正常",
            },
        },
        quote_items=[
            {"item_type": "part", "code": "P-001", "name": "刹车油 DOT4", "qty": 1, "unit_price": 68},
            {"item_type": "service", "code": "S-001", "name": "前制动系统检查", "qty": 1, "unit_price": 180},
        ],
    ),
    DemoCase(
        customer_name="测试客户JPG",
        phone="13912345678",
        email="demo.customer.jpg@drmoto.local",
        plate="TESTJPGOWH",
        make="Kawasaki",
        model="Ninja 400",
        year=2022,
        engine_code="399cc Twin",
        color="Green",
        description="客户上传图片，待补完整主诉",
        symptom_draft="客户上传图片，待补完整描述",
        symptom_confirmed="待门店进一步确认故障现象",
        quick_check={
            "odometer_km": None,
            "battery_voltage": None,
            "tire_front_psi": None,
            "tire_rear_psi": None,
            "engine_noise_note": "",
        },
        health_record={
            "measured_at": "2026-03-30T20:06:46+08:00",
            "odometer_km": 5600,
            "battery_voltage": 12.4,
            "oil_life_percent": 71,
            "notes": "演示图片工单，等待门店二次确认",
            "extra": {
                "image_case": "yes",
            },
        },
        quote_items=[],
    ),
    DemoCase(
        customer_name="张三",
        phone="13800138000",
        email="zhangsan@example.com",
        plate="沪BA01",
        make="Honda",
        model="CB400F",
        year=2021,
        engine_code="399cc",
        color="Pearl White",
        description="常规保养，检查刹车片（演示数据）",
        symptom_draft="常规保养到期，顺带检查前后刹车片厚度",
        symptom_confirmed="建议执行小保养，并确认刹车片剩余厚度",
        quick_check={
            "odometer_km": 8600,
            "battery_voltage": 12.5,
            "tire_front_psi": 32,
            "tire_rear_psi": 34,
            "engine_noise_note": "",
            "brake": "刹车片待复核",
        },
        health_record={
            "measured_at": "2026-03-29T18:30:00+08:00",
            "odometer_km": 8600,
            "battery_voltage": 12.5,
            "oil_life_percent": 52,
            "notes": "演示常规保养工单",
            "extra": {
                "brake_pads": "待复核",
            },
        },
        quote_items=[
            {"item_type": "part", "code": "P-101", "name": "机油 10W-40", "qty": 2, "unit_price": 118},
            {"item_type": "part", "code": "P-102", "name": "机油滤芯", "qty": 1, "unit_price": 45},
            {"item_type": "service", "code": "S-101", "name": "常规小保养", "qty": 1, "unit_price": 120},
        ],
    ),
]


def auth_session() -> requests.Session:
    session = requests.Session()
    token_resp = session.post(
        f"{BFF_URL}/auth/token",
        data={"username": USERNAME, "password": PASSWORD},
        timeout=TIMEOUT,
    )
    token_resp.raise_for_status()
    token = token_resp.json()["access_token"]
    session.headers.update({
        "Authorization": f"Bearer {token}",
        "X-Store-Id": STORE_ID,
    })
    return session


def ensure_customer_with_vehicle(session: requests.Session, case: DemoCase) -> tuple[int, str]:
    search = session.get(f"{BFF_URL}/ai/ops/context", params={"plate": case.plate}, timeout=TIMEOUT)
    search.raise_for_status()
    payload = search.json()
    matched_customer = payload.get("matched_customer") or {}
    if matched_customer.get("id"):
        return int(matched_customer["id"]), case.plate

    created = session.post(
        f"{BFF_URL}/mp/workorders/customers",
        json={
            "name": case.customer_name,
            "phone": case.phone,
            "email": case.email,
            "vehicles": [{
                "license_plate": case.plate,
                "make": case.make,
                "model": case.model,
                "year": case.year,
                "engine_code": case.engine_code,
                "color": case.color,
            }],
        },
        timeout=TIMEOUT,
    )
    created.raise_for_status()
    customer = created.json()
    return int(customer["id"]), case.plate


def ensure_work_order(session: requests.Session, customer_id: int, case: DemoCase) -> str:
    search = session.get(f"{BFF_URL}/ai/ops/context", params={"plate": case.plate}, timeout=TIMEOUT)
    search.raise_for_status()
    payload = search.json()
    matched_order = payload.get("matched_work_order") or {}
    if matched_order.get("id"):
        return str(matched_order["id"])

    created = session.post(
        f"{BFF_URL}/mp/workorders/",
        json={
            "customer_id": str(customer_id),
            "vehicle_plate": case.plate,
            "description": case.description,
        },
        timeout=TIMEOUT,
    )
    created.raise_for_status()
    return str(created.json()["id"])


def update_process_record(session: requests.Session, order_id: str, case: DemoCase) -> None:
    resp = session.put(
        f"{BFF_URL}/mp/workorders/{order_id}/process-record",
        json={
            "symptom_draft": case.symptom_draft,
            "symptom_confirmed": case.symptom_confirmed,
            "quick_check": case.quick_check,
        },
        timeout=TIMEOUT,
    )
    resp.raise_for_status()


def add_health_record(session: requests.Session, customer_id: int, case: DemoCase) -> None:
    resp = session.post(
        f"{BFF_URL}/mp/workorders/customers/{customer_id}/vehicles/{case.plate}/health-records",
        json=case.health_record,
        timeout=TIMEOUT,
    )
    resp.raise_for_status()


def add_quote(session: requests.Session, order_id: str, case: DemoCase) -> None:
    if not case.quote_items:
        return
    created = session.post(
        f"{BFF_URL}/mp/quotes/{order_id}/versions",
        json={
            "items": case.quote_items,
            "note": "演示数据报价单",
        },
        timeout=TIMEOUT,
    )
    created.raise_for_status()
    session.post(f"{BFF_URL}/mp/quotes/{order_id}/1/publish", timeout=TIMEOUT).raise_for_status()


def move_order(session: requests.Session, order_id: str, statuses: list[str]) -> None:
    for status in statuses:
        resp = session.post(
            f"{BFF_URL}/mp/workorders/{order_id}/status",
            params={"status": status},
            timeout=TIMEOUT,
        )
        if resp.status_code not in (200, 400):
            resp.raise_for_status()


def main() -> None:
    session = auth_session()
    summary: list[dict[str, Any]] = []

    for case in CASES:
        customer_id, plate = ensure_customer_with_vehicle(session, case)
        order_id = ensure_work_order(session, customer_id, case)
        update_process_record(session, order_id, case)
        add_health_record(session, customer_id, case)
        add_quote(session, order_id, case)
        move_order(session, order_id, ["confirmed", "quoted"])
        summary.append({
            "customer_id": customer_id,
            "plate": plate,
            "work_order_id": order_id,
        })

    print(json.dumps({"seeded_cases": summary}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
