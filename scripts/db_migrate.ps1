param(
    [string]$ComposeFile = "infra/docker-compose.yml"
)

$ErrorActionPreference = "Stop"

Write-Host "Applying BFF DB migrations..." -ForegroundColor Cyan
docker compose -f $ComposeFile exec -T bff python3 -m app.core.migrations

Write-Host "Migration step completed." -ForegroundColor Green
