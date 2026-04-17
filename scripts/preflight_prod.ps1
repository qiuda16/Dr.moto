param(
    [string]$ComposeFile = "infra/docker-compose.yml",
    [string]$BaseUrl = "http://localhost:8080",
    [string]$AdminUsername = "admin",
    [string]$AdminPassword = "",
    [string]$ExpectedEnv = "",
    [switch]$CheckReady,
    [switch]$RunMigrations
)

$ErrorActionPreference = "Stop"

Write-Host "[1/4] Checking container status..." -ForegroundColor Cyan
docker compose -f $ComposeFile ps

Write-Host "[2/4] Checking BFF health..." -ForegroundColor Cyan
$health = Invoke-RestMethod -Uri "$BaseUrl/health" -Method Get
$health | ConvertTo-Json -Depth 6 | Write-Host
if ($health.status -ne "ok") {
    throw "BFF health is not ok."
}
if ($ExpectedEnv -and $health.env -ne $ExpectedEnv) {
    throw "BFF runtime env mismatch. expected=$ExpectedEnv actual=$($health.env)"
}
if ($CheckReady) {
    $readyResp = Invoke-WebRequest -Uri "$BaseUrl/health/ready" -Method Get
    if ($readyResp.StatusCode -ne 200) {
        throw "BFF readiness HTTP status is not 200."
    }
    $readyBody = $readyResp.Content | ConvertFrom-Json
    if ($readyBody.status -ne "ok" -and $readyBody.status -ne "ready") {
        throw "BFF readiness status is not ok."
    }
}

Write-Host "[3/4] Checking Odoo module state..." -ForegroundColor Cyan
$moduleState = docker compose -f $ComposeFile exec -T db psql -U odoo -d odoo -t -A -c "select state from ir_module_module where name='drmoto_mro';"
$moduleState = $moduleState.Trim()
Write-Host "drmoto_mro state: $moduleState"
if ($moduleState -ne "installed") {
    throw "drmoto_mro is not installed."
}

Write-Host "[4/4] Smoke auth token..." -ForegroundColor Cyan
if (-not $AdminPassword) {
    if ($env:BFF_ADMIN_PASSWORD) {
        $AdminPassword = $env:BFF_ADMIN_PASSWORD
    } else {
        throw "Admin password is required. Set -AdminPassword or BFF_ADMIN_PASSWORD."
    }
}

$tokenResp = Invoke-RestMethod -Uri "$BaseUrl/auth/token" -Method Post -ContentType "application/x-www-form-urlencoded" -Body "username=$AdminUsername&password=$AdminPassword"
if (-not $tokenResp.access_token) {
    throw "Failed to acquire token."
}

if ($RunMigrations) {
    Write-Host "[extra] Applying DB migrations..." -ForegroundColor Cyan
    docker compose -f $ComposeFile exec -T bff python3 -m app.core.migrations
}

Write-Host "Preflight passed." -ForegroundColor Green
