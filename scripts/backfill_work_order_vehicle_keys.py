from __future__ import annotations

import os
import sys


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "bff"))

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")

from app.core.db import SessionLocal  # noqa: E402
from app.models import WorkOrder  # noqa: E402
from app.routers.work_orders import _parse_positive_int, _resolve_work_order_vehicle_key  # noqa: E402


def main() -> int:
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
        print(
            {
                "scanned": len(rows),
                "updated": updated,
                "skipped": skipped,
            }
        )
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
