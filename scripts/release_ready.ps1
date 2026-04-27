param(
    [string]$PythonExe = "C:\Users\WIN10\AppData\Local\Python\pythoncore-3.14-64\python.exe",
    [string]$ComposeFile = "infra/docker-compose.yml",
    [string]$BaseUrl = "http://localhost:18080",
    [string]$AdminUsername = "admin",
    [string]$AdminPassword = "",
    [string]$StoreId = "default",
    [string]$ExpectedEnv = "",
    [switch]$CheckReady,
    [switch]$RunReleaseGate,
    [switch]$RunProdCutover,
    [switch]$SkipBackup,
    [switch]$RunAiEnterpriseBrutal,
    [string]$AiBaseUrl = "http://127.0.0.1:18080",
    [string]$AiAdminUsername = "admin",
    [string]$AiAdminPassword = ""
)

$ErrorActionPreference = "Stop"
[Console]::InputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$PSDefaultParameterValues['Out-File:Encoding'] = 'utf8'
$PSDefaultParameterValues['Set-Content:Encoding'] = 'utf8'

$repoRoot = Split-Path -Parent $PSScriptRoot
$reportDir = Join-Path $repoRoot "infra\reports\release_ready"
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$reportPath = Join-Path $reportDir "$timestamp.json"
New-Item -ItemType Directory -Force -Path $reportDir | Out-Null

function Invoke-ChildScript {
    param(
        [Parameter(Mandatory = $true)][string]$ScriptPath,
        [string[]]$Arguments = @()
    )
    & powershell -NoProfile -ExecutionPolicy Bypass -File $ScriptPath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Script failed: $ScriptPath (exit code: $LASTEXITCODE)"
    }
}

function Invoke-Step {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][scriptblock]$Action
    )
    Write-Host "==> $Name" -ForegroundColor Cyan
    $start = Get-Date
    & $Action
    $end = Get-Date
    [pscustomobject]@{
        name = $Name
        started_at = $start.ToString("s")
        finished_at = $end.ToString("s")
        duration_seconds = [math]::Round(($end - $start).TotalSeconds, 2)
        status = "passed"
    }
}

if (($RunReleaseGate -or $RunProdCutover) -and -not $AdminPassword) {
    if ($env:BFF_ADMIN_PASSWORD) {
        $AdminPassword = $env:BFF_ADMIN_PASSWORD
    } else {
        throw "Admin password is required for release_gate/cutover. Set -AdminPassword or BFF_ADMIN_PASSWORD."
    }
}

$steps = @()
try {
    if (-not $AiAdminPassword -and $env:BFF_ADMIN_PASSWORD) {
        $AiAdminPassword = $env:BFF_ADMIN_PASSWORD
    }

    $preAuditArgs = @(
        "-PythonExe", $PythonExe
    )
    if ($RunAiEnterpriseBrutal) {
        $preAuditArgs += @(
            "-RunAiEnterpriseBrutal",
            "-AiBaseUrl", $AiBaseUrl,
            "-AiAdminUsername", $AiAdminUsername
        )
        if ($AiAdminPassword) {
            $preAuditArgs += @("-AiAdminPassword", $AiAdminPassword)
        }
    }

    $steps += Invoke-Step -Name "pre_release_audit" -Action {
        Invoke-ChildScript -ScriptPath "scripts/pre_release_audit.ps1" -Arguments $preAuditArgs
    }

    if ($RunReleaseGate) {
        $releaseArgs = @(
            "-ComposeFile", $ComposeFile,
            "-BaseUrl", $BaseUrl,
            "-AdminUsername", $AdminUsername,
            "-AdminPassword", $AdminPassword,
            "-StoreId", $StoreId
        )
        if ($ExpectedEnv) {
            $releaseArgs += @("-ExpectedEnv", $ExpectedEnv)
        }
        if ($CheckReady) {
            $releaseArgs += "-CheckReady"
        }
        if ($SkipBackup) {
            $releaseArgs += "-SkipBackup"
        }
        $steps += Invoke-Step -Name "release_gate" -Action {
            Invoke-ChildScript -ScriptPath "scripts/release_gate.ps1" -Arguments $releaseArgs
        }
    }

    if ($RunProdCutover) {
        $cutoverArgs = @(
            "-ComposeFile", $ComposeFile,
            "-BaseUrl", $BaseUrl,
            "-AdminUsername", $AdminUsername,
            "-AdminPassword", $AdminPassword,
            "-StoreId", $StoreId
        )
        if ($ExpectedEnv) {
            $cutoverArgs += @("-ExpectedEnv", $ExpectedEnv)
        }
        if ($SkipBackup) {
            $cutoverArgs += "-SkipBackup"
        }
        $steps += Invoke-Step -Name "cutover_prod" -Action {
            Invoke-ChildScript -ScriptPath "scripts/cutover_prod.ps1" -Arguments $cutoverArgs
        }
    }

    $report = [pscustomobject]@{
        generated_at = (Get-Date).ToString("s")
        status = "passed"
        mode = if ($RunProdCutover) { "pre_release_audit+cutover_prod" } elseif ($RunReleaseGate) { "pre_release_audit+release_gate" } else { "pre_release_audit_only" }
        steps = $steps
    }
    $report | ConvertTo-Json -Depth 6 | Set-Content -Path $reportPath -Encoding UTF8
    Write-Host "Release-ready workflow passed." -ForegroundColor Green
    Write-Host "Report: $reportPath" -ForegroundColor Green
}
catch {
    $steps += [pscustomobject]@{
        name = "failed"
        status = "failed"
        error = $_.Exception.Message
    }
    $report = [pscustomobject]@{
        generated_at = (Get-Date).ToString("s")
        status = "failed"
        steps = $steps
    }
    $report | ConvertTo-Json -Depth 6 | Set-Content -Path $reportPath -Encoding UTF8
    Write-Error "Release-ready workflow failed. Report: $reportPath"
    throw
}
