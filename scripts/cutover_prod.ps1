param(
    [string]$EnvFile = "infra/.env",
    [string]$ComposeFile = "infra/docker-compose.yml",
    [string]$BaseUrl = "http://localhost:8080",
    [string]$AdminUsername = "admin",
    [string]$AdminPassword = "",
    [string]$StoreId = "default",
    [string]$ExpectedEnv = "prod",
    [switch]$SkipBackup
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

Write-Host "[1/4] Validate production env..." -ForegroundColor Cyan
Invoke-PsScript -ScriptPath "scripts/validate_prod_env.ps1" -Arguments @(
    "-EnvFile", $EnvFile,
    "-ExpectedEnv", $ExpectedEnv,
    "-Strict",
    "-FailOnWarnings"
)

Write-Host "[2/4] Run release gate..." -ForegroundColor Cyan
$releaseArgs = @(
    "-ComposeFile", $ComposeFile,
    "-BaseUrl", $BaseUrl,
    "-AdminUsername", $AdminUsername,
    "-AdminPassword", $AdminPassword,
    "-StoreId", $StoreId,
    "-ExpectedEnv", $ExpectedEnv,
    "-CheckReady"
)
if ($SkipBackup) {
    $releaseArgs += "-SkipBackup"
}
Invoke-PsScript -ScriptPath "scripts/release_gate.ps1" -Arguments $releaseArgs

Write-Host "[3/4] Run alert threshold check..." -ForegroundColor Cyan
Invoke-PsScript -ScriptPath "scripts/alert_check.ps1" -Arguments @(
    "-BaseUrl", $BaseUrl
)

Write-Host "[4/4] Export acceptance pack..." -ForegroundColor Cyan
Invoke-PsScript -ScriptPath "scripts/export_acceptance_pack.ps1" -Arguments @(
    "-ComposeFile", $ComposeFile,
    "-BaseUrl", $BaseUrl
)

Write-Host "Production cutover workflow passed." -ForegroundColor Green
