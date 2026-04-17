from __future__ import annotations

import json
import os
import subprocess
import sys
from typing import Any


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_CONTAINER = os.environ.get("DRMOTO_DB_CONTAINER", "infra-db-1")
DEFAULT_DB = os.environ.get("DRMOTO_DB_NAME", "bff")
DEFAULT_USER = os.environ.get("DRMOTO_DB_USER", "odoo")


def run_psql(sql: str) -> list[dict[str, Any]]:
    command = [
        "docker",
        "exec",
        DEFAULT_CONTAINER,
        "psql",
        "-U",
        DEFAULT_USER,
        "-d",
        DEFAULT_DB,
        "-t",
        "-A",
        "-F",
        "|",
        "-c",
        sql,
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=True)
    rows: list[dict[str, Any]] = []
    for line in result.stdout.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        columns = stripped.split("|")
        rows.append({"columns": columns})
    return rows


def one_value(sql: str) -> str:
    rows = run_psql(sql)
    if not rows:
        return ""
    return rows[0]["columns"][0]


def gather_report() -> dict[str, Any]:
    report: dict[str, Any] = {}

    report["schema_migration_count"] = int(
        one_value("SELECT COUNT(*) FROM schema_migrations;") or "0"
    )
    report["latest_migrations"] = [
        row["columns"][0]
        for row in run_psql(
            "SELECT version FROM schema_migrations ORDER BY version DESC LIMIT 5;"
        )
    ]
    report["foreign_key_count"] = int(
        one_value(
            "SELECT COUNT(*) "
            "FROM pg_constraint c "
            "JOIN pg_namespace n ON n.oid = c.connamespace "
            "WHERE c.contype = 'f' AND n.nspname = 'public';"
        )
        or "0"
    )
    report["vehicles_count"] = int(one_value("SELECT COUNT(*) FROM vehicles;") or "0")
    report["catalog_models_count"] = int(
        one_value("SELECT COUNT(*) FROM vehicle_catalog_models;") or "0"
    )
    report["procedure_vehicle_orphans"] = int(
        one_value(
            "SELECT COUNT(*) "
            "FROM procedures p "
            "LEFT JOIN vehicles v ON v.key = p.vehicle_key "
            "WHERE p.vehicle_key IS NOT NULL AND v.key IS NULL;"
        )
        or "0"
    )
    report["segment_vehicle_bridge_gaps"] = int(
        one_value(
            "SELECT COUNT(*) "
            "FROM vehicle_knowledge_segments s "
            "LEFT JOIN vehicles v ON v.key = ('CATALOG_MODEL:' || s.model_id::text) "
            "WHERE s.model_id IS NOT NULL AND v.key IS NULL;"
        )
        or "0"
    )
    report["quote_work_order_orphans"] = int(
        one_value(
            "SELECT COUNT(*) "
            "FROM quotes q "
            "LEFT JOIN work_orders w ON w.uuid = q.work_order_uuid "
            "WHERE w.uuid IS NULL;"
        )
        or "0"
    )
    report["work_order_vehicle_key_nulls"] = int(
        one_value(
            "SELECT COUNT(*) "
            "FROM work_orders "
            "WHERE vehicle_key IS NULL;"
        )
        or "0"
    )
    report["work_order_vehicle_key_filled"] = int(
        one_value(
            "SELECT COUNT(*) "
            "FROM work_orders "
            "WHERE vehicle_key IS NOT NULL;"
        )
        or "0"
    )
    report["work_order_vehicle_key_unresolved_non_test"] = int(
        one_value(
            "SELECT COUNT(*) "
            "FROM work_orders "
            "WHERE vehicle_key IS NULL "
            "AND uuid NOT LIKE 'test-%';"
        )
        or "0"
    )
    report["work_order_vehicle_key_unresolved_test"] = int(
        one_value(
            "SELECT COUNT(*) "
            "FROM work_orders "
            "WHERE vehicle_key IS NULL "
            "AND uuid LIKE 'test-%';"
        )
        or "0"
    )
    report["settings_table_exists"] = (
        one_value(
            "SELECT EXISTS ("
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = 'app_settings'"
            ");"
        ).lower()
        == "t"
    )
    return report


def main() -> int:
    try:
        report = gather_report()
    except subprocess.CalledProcessError as exc:
        sys.stderr.write(exc.stderr or str(exc))
        return 1

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
