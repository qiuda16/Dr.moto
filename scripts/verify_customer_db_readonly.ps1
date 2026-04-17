param(
  [Parameter(Mandatory = $false)]
  [string]$DatabaseUrl,
  [Parameter(Mandatory = $false)]
  [string]$ContainerName = "infra-bff-1"
)

$ErrorActionPreference = "Stop"

if (-not $DatabaseUrl) {
  Write-Host "[INFO] No DatabaseUrl provided, checking current container DATABASE_URL."
}

$pythonCode = @"
import os
from sqlalchemy import create_engine, text

url = os.getenv("DATABASE_URL")
if not url:
    print("[FAIL] DATABASE_URL is empty")
    raise SystemExit(2)

engine = create_engine(url, pool_pre_ping=True)
critical_tables = [
    "vehicles",
    "vehicle_health_records",
    "work_orders",
    "work_order_process_records",
    "customer_wechat_bindings",
    "customer_auth_sessions",
]

with engine.connect() as conn:
    conn.execute(text("SELECT 1"))
    db_name = conn.execute(text("select current_database()")).scalar()
    print(f"[OK] Connected database: {db_name}")

    for t in critical_tables:
        exists = conn.execute(
            text("select exists (select 1 from information_schema.tables where table_schema='public' and table_name=:name)"),
            {"name": t},
        ).scalar()
        status = "present" if exists else "missing"
        print(f"[TABLE] {t}: {status}")
"@

if ($DatabaseUrl) {
  $pythonCode | docker exec -i -e "DATABASE_URL=$DatabaseUrl" $ContainerName python3 -
} else {
  $pythonCode | docker exec -i $ContainerName python3 -
}
