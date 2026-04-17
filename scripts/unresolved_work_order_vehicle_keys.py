from __future__ import annotations

import json
import os
import subprocess
import sys


DEFAULT_CONTAINER = os.environ.get("DRMOTO_BFF_CONTAINER", "infra-bff-1")


PY_CODE = r"""
import json
from app.core.db import SessionLocal
from app.models import WorkOrder
from app.integrations.odoo import odoo_client

db = SessionLocal()
try:
    rows = (
        db.query(WorkOrder)
        .filter(WorkOrder.vehicle_key.is_(None), ~WorkOrder.uuid.like('test-%'))
        .order_by(WorkOrder.created_at.desc(), WorkOrder.id.desc())
        .all()
    )
    report = []
    for row in rows:
        customer_id = int(row.customer_id) if str(row.customer_id).isdigit() else None
        any_vehicle_rows = []
        if customer_id:
            any_vehicle_rows = odoo_client.execute_kw(
                'drmoto.partner.vehicle',
                'search_read',
                [[['partner_id', '=', customer_id]]],
                {'fields': ['id', 'license_plate', 'vehicle_id'], 'limit': 5},
            )
        report.append({
            'uuid': row.uuid,
            'odoo_id': row.odoo_id,
            'customer_id': row.customer_id,
            'vehicle_plate': row.vehicle_plate,
            'status': row.status,
            'has_partner_vehicle_records': bool(any_vehicle_rows),
            'reason': 'missing_customer_vehicle_records' if not any_vehicle_rows else 'unresolved_match',
        })
    print(json.dumps(report, ensure_ascii=False, indent=2))
finally:
    db.close()
"""


def main() -> int:
    result = subprocess.run(
        ["docker", "exec", "-i", DEFAULT_CONTAINER, "python3", "-c", PY_CODE],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
        return result.returncode
    print(result.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
