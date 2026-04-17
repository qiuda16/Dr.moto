param(
    [Parameter(Mandatory = $true)]
    [string]$BackupDir,
    [string]$ComposeFile = "infra/docker-compose.yml",
    [string]$BaseUrl = "http://localhost:8080",
    [string]$AdminUsername = "admin",
    [string]$AdminPassword = "",
    [string]$StoreId = "default"
)

$ErrorActionPreference = "Stop"

function Invoke-PsScript {
    param(
        [Parameter(Mandatory = $true)][string]$ScriptPath,
        [string[]]$Arguments = @()
    )
    & powershell -ExecutionPolicy Bypass -File $ScriptPath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Script failed: $ScriptPath (exit code: $LASTEXITCODE)"
    }
}

if (-not $AdminPassword) {
    if ($env:BFF_ADMIN_PASSWORD) {
        $AdminPassword = $env:BFF_ADMIN_PASSWORD
    } else {
        throw "Admin password is required. Set -AdminPassword or BFF_ADMIN_PASSWORD."
    }
}

Write-Host "[1/5] Restore stack from backup..." -ForegroundColor Yellow
Invoke-PsScript -ScriptPath "scripts/restore_stack.ps1" -Arguments @(
    "-BackupDir", $BackupDir,
    "-ComposeFile", $ComposeFile
)

Write-Host "[2/5] Ensure BFF image/service..." -ForegroundColor Cyan
docker compose -f $ComposeFile up -d --build bff

Write-Host "[3/5] Re-apply DB migrations (idempotent)..." -ForegroundColor Cyan
Invoke-PsScript -ScriptPath "scripts/db_migrate.ps1" -Arguments @(
    "-ComposeFile", $ComposeFile
)

Write-Host "[4/5] Preflight verification..." -ForegroundColor Cyan
Invoke-PsScript -ScriptPath "scripts/preflight_prod.ps1" -Arguments @(
    "-ComposeFile", $ComposeFile,
    "-BaseUrl", $BaseUrl,
    "-AdminUsername", $AdminUsername,
    "-AdminPassword", $AdminPassword
)

Write-Host "[5/5] Smoke verification..." -ForegroundColor Cyan
Invoke-PsScript -ScriptPath "scripts/smoke_test.ps1" -Arguments @(
    "-BaseUrl", $BaseUrl,
    "-Username", $AdminUsername,
    "-Password", $AdminPassword,
    "-StoreId", $StoreId
)

Write-Host "Rollback workflow passed." -ForegroundColor Green
