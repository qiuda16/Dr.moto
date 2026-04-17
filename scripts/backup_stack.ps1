param(
    [string]$ComposeFile = "infra/docker-compose.yml",
    [string]$BackupRoot = "infra/backups"
)

$ErrorActionPreference = "Stop"

$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$targetDir = Join-Path $BackupRoot $ts
New-Item -ItemType Directory -Path $targetDir -Force | Out-Null

Write-Host "Backup target: $targetDir" -ForegroundColor Cyan

Write-Host "[1/3] Dump database bff..." -ForegroundColor Cyan
docker compose -f $ComposeFile exec -T db pg_dump -U odoo -d bff | Out-File -FilePath (Join-Path $targetDir "bff.sql") -Encoding utf8

Write-Host "[2/3] Dump database odoo..." -ForegroundColor Cyan
docker compose -f $ComposeFile exec -T db pg_dump -U odoo -d odoo | Out-File -FilePath (Join-Path $targetDir "odoo.sql") -Encoding utf8

Write-Host "[3/3] Copy MinIO data..." -ForegroundColor Cyan
$minioDir = Join-Path $targetDir "minio_data"
New-Item -ItemType Directory -Path $minioDir -Force | Out-Null
docker compose -f $ComposeFile cp minio:/data $minioDir

Write-Host "Backup completed: $targetDir" -ForegroundColor Green
