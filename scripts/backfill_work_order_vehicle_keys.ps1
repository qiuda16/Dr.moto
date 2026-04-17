$ErrorActionPreference = "Stop"

$code = @'
from app.core.db import SessionLocal
from app.models import WorkOrder
from app.routers.work_orders import _parse_positive_int, _resolve_work_order_vehicle_key

db = SessionLocal()
try:
    rows = (
        db.query(WorkOrder)
        .filter(WorkOrder.vehicle_key.is_(None))
        .order_by(WorkOrder.id.asc())
        .all()
    )
    updated = 0
    skipped = 0
    for row in rows:
        customer_id = _parse_positive_int(row.customer_id)
        vehicle_key = _resolve_work_order_vehicle_key(db, customer_id, row.vehicle_plate)
        if not vehicle_key:
            skipped += 1
            continue
        row.vehicle_key = vehicle_key
        updated += 1
    db.commit()
    print({"scanned": len(rows), "updated": updated, "skipped": skipped})
finally:
    db.close()
'@

$code | docker exec -i infra-bff-1 python3 -
