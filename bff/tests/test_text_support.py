from app.core.text import build_storage_object_name, compact_whitespace
from app.schemas.customer import CustomerCreate
from app.schemas.work_order import WorkOrderCreate


def test_compact_whitespace_keeps_chinese():
    assert compact_whitespace("  \u5f20\u4e09  \u7ef4\u4fee  ") == "\u5f20\u4e09 \u7ef4\u4fee"


def test_customer_create_accepts_chinese_text():
    payload = CustomerCreate(
        name=" \u5f20\u4e09 ",
        phone=" 13800138000 ",
        email=" test@example.com "
    )

    assert payload.name == "\u5f20\u4e09"
    assert payload.phone == "13800138000"
    assert payload.email == "test@example.com"


def test_work_order_create_accepts_chinese_text():
    payload = WorkOrderCreate(
        customer_id="\u5ba2\u6237001",
        vehicle_plate="\u7ca4B12345",
        description="\u53d1\u52a8\u673a\u5f02\u54cd\uff0c\u9700\u8981\u8fdb\u4e00\u6b65\u68c0\u6d4b"
    )

    assert payload.customer_id == "\u5ba2\u6237001"
    assert payload.vehicle_plate == "\u7ca4B12345"
    assert payload.description == "\u53d1\u52a8\u673a\u5f02\u54cd\uff0c\u9700\u8981\u8fdb\u4e00\u6b65\u68c0\u6d4b"


def test_storage_object_name_is_ascii_safe():
    object_name = build_storage_object_name(
        "work-orders/test",
        "\u7ef4\u4fee\u7167\u7247-\u5de6\u524d\u8f6e.JPG"
    )

    assert object_name.startswith("work-orders/test/")
    assert object_name.endswith(".jpg")
    assert object_name.isascii()
