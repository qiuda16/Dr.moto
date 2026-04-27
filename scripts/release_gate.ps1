param(
    [string]$ComposeFile = "infra/docker-compose.yml",
    [string]$BaseUrl = "http://localhost:18080",
    [string]$AdminUsername = "admin",
    [string]$AdminPassword = "",
    [string]$StoreId = "default",
    [string]$ExpectedEnv = "",
    [switch]$CheckReady,
    [switch]$SkipBackup
)

$ErrorActionPreference = "Stop"

function Invoke-PsScript {
    param(
        [Parameter(Mandatory = $true)][string]$ScriptPath,
        [string[]]$Arguments = @()
    )
    & powershell -NoProfile -ExecutionPolicy Bypass -File $ScriptPath @Arguments
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

Write-Host "[1/5] Build and start BFF..." -ForegroundColor Cyan
docker compose -f $ComposeFile up -d --build bff

if (-not $SkipBackup) {
    Write-Host "[2/5] Backup stack..." -ForegroundColor Cyan
    Invoke-PsScript -ScriptPath "scripts/backup_stack.ps1" -Arguments @(
        "-ComposeFile", $ComposeFile
    )
} else {
    Write-Host "[2/5] Backup skipped by parameter." -ForegroundColor Yellow
}

Write-Host "[3/5] Apply DB migrations..." -ForegroundColor Cyan
Invoke-PsScript -ScriptPath "scripts/db_migrate.ps1" -Arguments @(
    "-ComposeFile", $ComposeFile
)

Write-Host "[4/5] Preflight checks..." -ForegroundColor Cyan
$preflightArgs = @(
    "-ComposeFile", $ComposeFile,
    "-BaseUrl", $BaseUrl,
    "-AdminUsername", $AdminUsername,
    "-AdminPassword", $AdminPassword
)
if ($ExpectedEnv) {
    $preflightArgs += @("-ExpectedEnv", $ExpectedEnv)
}
if ($CheckReady) {
    $preflightArgs += "-CheckReady"
}
Invoke-PsScript -ScriptPath "scripts/preflight_prod.ps1" -Arguments $preflightArgs

Write-Host "[5/5] Smoke test..." -ForegroundColor Cyan
Invoke-PsScript -ScriptPath "scripts/smoke_test.ps1" -Arguments @(
    "-BaseUrl", $BaseUrl,
    "-Username", $AdminUsername,
    "-Password", $AdminPassword,
    "-StoreId", $StoreId
)

Write-Host "Release gate passed." -ForegroundColor Green
