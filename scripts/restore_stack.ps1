param(
    [Parameter(Mandatory = $true)]
    [string]$BackupDir,
    [string]$ComposeFile = "infra/docker-compose.yml"
)

$ErrorActionPreference = "Stop"

$bffDump = Join-Path $BackupDir "bff.sql"
$odooDump = Join-Path $BackupDir "odoo.sql"
$minioDataDir = Join-Path $BackupDir "minio_data\data"

if (-not (Test-Path $bffDump)) { throw "Missing backup file: $bffDump" }
if (-not (Test-Path $odooDump)) { throw "Missing backup file: $odooDump" }

Write-Host "Restoring from: $BackupDir" -ForegroundColor Yellow

Write-Host "[1/6] Stopping app services..." -ForegroundColor Cyan
docker compose -f $ComposeFile stop bff odoo

Write-Host "[2/6] Recreate database bff..." -ForegroundColor Cyan
docker compose -f $ComposeFile exec -T db psql -U odoo -d postgres -c "DROP DATABASE IF EXISTS bff WITH (FORCE);"
docker compose -f $ComposeFile exec -T db psql -U odoo -d postgres -c "CREATE DATABASE bff OWNER odoo;"

Write-Host "[3/6] Recreate database odoo..." -ForegroundColor Cyan
docker compose -f $ComposeFile exec -T db psql -U odoo -d postgres -c "DROP DATABASE IF EXISTS odoo WITH (FORCE);"
docker compose -f $ComposeFile exec -T db psql -U odoo -d postgres -c "CREATE DATABASE odoo OWNER odoo;"

Write-Host "[4/6] Restore SQL dumps..." -ForegroundColor Cyan
Get-Content $bffDump | docker compose -f $ComposeFile exec -T db psql -U odoo -d bff
Get-Content $odooDump | docker compose -f $ComposeFile exec -T db psql -U odoo -d odoo

if (Test-Path $minioDataDir) {
    Write-Host "[5/6] Restore MinIO object data..." -ForegroundColor Cyan
    docker compose -f $ComposeFile exec -T minio sh -c "rm -rf /data/*"
    docker compose -f $ComposeFile cp $minioDataDir minio:/data
} else {
    Write-Host "[5/6] Skip MinIO restore (no minio_data\data found)." -ForegroundColor Yellow
}

Write-Host "[6/6] Starting app services..." -ForegroundColor Cyan
docker compose -f $ComposeFile up -d odoo bff

Write-Host "Restore completed." -ForegroundColor Green
