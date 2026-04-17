param(
    [string]$ComposeFile = "infra/docker-compose.yml",
    [string]$BaseUrl = "http://localhost:8080",
    [string]$OutputRoot = "infra/reports/acceptance"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $OutputRoot)) {
    New-Item -ItemType Directory -Path $OutputRoot -Force | Out-Null
}

$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$packDir = Join-Path $OutputRoot $ts
New-Item -ItemType Directory -Path $packDir -Force | Out-Null

Write-Host "[1/6] Export container status..." -ForegroundColor Cyan
$psOutput = docker compose -f $ComposeFile ps
$psOutput | Out-File -FilePath (Join-Path $packDir "docker_compose_ps.txt") -Encoding utf8

Write-Host "[2/6] Export service health..." -ForegroundColor Cyan
$health = Invoke-RestMethod -Uri "$BaseUrl/health" -Method Get
$ready = Invoke-RestMethod -Uri "$BaseUrl/health/ready" -Method Get
$health | ConvertTo-Json -Depth 8 | Out-File -FilePath (Join-Path $packDir "health.json") -Encoding utf8
$ready | ConvertTo-Json -Depth 8 | Out-File -FilePath (Join-Path $packDir "ready.json") -Encoding utf8

Write-Host "[3/6] Export metrics snapshot..." -ForegroundColor Cyan
$metrics = Invoke-WebRequest -Uri "$BaseUrl/metrics" -Method Get
$metrics.Content | Out-File -FilePath (Join-Path $packDir "metrics.prom") -Encoding utf8

Write-Host "[4/6] Export migration status..." -ForegroundColor Cyan
$migrationState = docker compose -f $ComposeFile exec -T db psql -U odoo -d bff -t -A -c "select version from schema_migrations order by applied_at asc;"
$migrationState | Out-File -FilePath (Join-Path $packDir "schema_migrations.txt") -Encoding utf8

Write-Host "[5/6] Attach latest alert report..." -ForegroundColor Cyan
$alertDir = "infra/reports/alerts"
if (Test-Path $alertDir) {
    $latestAlert = Get-ChildItem -Path $alertDir -Filter "*.json" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($latestAlert) {
        Copy-Item -Path $latestAlert.FullName -Destination (Join-Path $packDir "latest_alert.json") -Force
    }
}

Write-Host "[6/6] Write acceptance index..." -ForegroundColor Cyan
$index = @"
Acceptance Pack
GeneratedAt: $(Get-Date -Format o)
BaseUrl: $BaseUrl
ComposeFile: $ComposeFile

Artifacts:
- docker_compose_ps.txt
- health.json
- ready.json
- metrics.prom
- schema_migrations.txt
- latest_alert.json (if exists)
"@
$index | Out-File -FilePath (Join-Path $packDir "README.txt") -Encoding utf8

Write-Host ("Acceptance pack exported: {0}" -f $packDir) -ForegroundColor Green
