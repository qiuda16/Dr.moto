param(
    [string]$PythonExe = "C:\Users\WIN10\AppData\Local\Python\pythoncore-3.14-64\python.exe",
    [switch]$SkipFrontendBuild,
    [switch]$SkipBackendTests,
    [switch]$SkipDbAudit,
    [switch]$SkipEncodingAudit,
    [switch]$SkipChinesePathSmoke,
    [switch]$SkipSecretScan,
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
$reportDir = Join-Path $repoRoot "infra\reports\pre_release_audit"
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$reportPath = Join-Path $reportDir "$timestamp.json"

New-Item -ItemType Directory -Force -Path $reportDir | Out-Null

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

$steps = @()

try {
    $steps += Invoke-Step -Name "git_status_cleanliness" -Action {
        Push-Location $repoRoot
        try {
            $gitStatus = git status --short
            if ($LASTEXITCODE -ne 0) {
                throw "git status failed"
            }
            if ($gitStatus) {
                Write-Warning "Working tree is not clean."
                $gitStatus
            }
        } finally {
            Pop-Location
        }
    }

    if (-not $SkipBackendTests) {
        $steps += Invoke-Step -Name "backend_pytest" -Action {
            Push-Location $repoRoot
            try {
                & $PythonExe -m pytest .\bff\tests
                if ($LASTEXITCODE -ne 0) {
                    throw "Backend pytest failed"
                }
            } finally {
                Pop-Location
            }
        }
    }

    if (-not $SkipFrontendBuild) {
        $steps += Invoke-Step -Name "web_staff_build" -Action {
            Push-Location (Join-Path $repoRoot "clients\web_staff")
            try {
                npm.cmd run build
                if ($LASTEXITCODE -ne 0) {
                    throw "Frontend build failed"
                }
            } finally {
                Pop-Location
            }
        }
    }

    if (-not $SkipDbAudit) {
        $steps += Invoke-Step -Name "db_integrity_audit" -Action {
            Push-Location $repoRoot
            try {
                & $PythonExe .\scripts\db_integrity_audit.py
                if ($LASTEXITCODE -ne 0) {
                    throw "DB integrity audit failed"
                }
            } finally {
                Pop-Location
            }
        }
    }

    if (-not $SkipEncodingAudit) {
        $steps += Invoke-Step -Name "encoding_audit" -Action {
            Push-Location $repoRoot
            try {
                & $PythonExe .\scripts\encoding_audit.py
                if ($LASTEXITCODE -ne 0) {
                    throw "Encoding audit failed"
                }
            } finally {
                Pop-Location
            }
        }
    }

    if (-not $SkipChinesePathSmoke) {
        $steps += Invoke-Step -Name "chinese_path_smoke" -Action {
            Push-Location $repoRoot
            try {
                & $PythonExe .\scripts\chinese_path_smoke.py
                if ($LASTEXITCODE -ne 0) {
                    throw "Chinese path smoke test failed"
                }
            } finally {
                Pop-Location
            }
        }
    }

    if (-not $SkipSecretScan) {
        $steps += Invoke-Step -Name "secret_scan" -Action {
            Push-Location $repoRoot
            try {
                & $PythonExe .\scripts\secret_scan.py
                if ($LASTEXITCODE -ne 0) {
                    throw "Secret scan failed"
                }
            } finally {
                Pop-Location
            }
        }
    }

    if ($RunAiEnterpriseBrutal) {
        if (-not $AiAdminPassword) {
            if ($env:BFF_ADMIN_PASSWORD) {
                $AiAdminPassword = $env:BFF_ADMIN_PASSWORD
            } else {
                throw "AI enterprise brutal suite requires admin password. Set -AiAdminPassword or BFF_ADMIN_PASSWORD."
            }
        }

        $steps += Invoke-Step -Name "ai_enterprise_brutal_suite" -Action {
            Push-Location $repoRoot
            try {
                & $PythonExe .\scripts\ai_enterprise_brutal_suite.py --base-url $AiBaseUrl --username $AiAdminUsername --password $AiAdminPassword --workspace .
                if ($LASTEXITCODE -ne 0) {
                    throw "AI enterprise brutal suite failed"
                }
            } finally {
                Pop-Location
            }
        }
    }

    $report = [pscustomobject]@{
        generated_at = (Get-Date).ToString("s")
        status = "passed"
        steps = $steps
    }
    $report | ConvertTo-Json -Depth 5 | Set-Content -Path $reportPath -Encoding UTF8
    Write-Host "Pre-release audit passed." -ForegroundColor Green
    Write-Host "Report: $reportPath" -ForegroundColor Green
}
catch {
    $failedStep = [pscustomobject]@{
        name = "failed"
        status = "failed"
        error = $_.Exception.Message
    }
    $steps += $failedStep
    $report = [pscustomobject]@{
        generated_at = (Get-Date).ToString("s")
        status = "failed"
        steps = $steps
    }
    $report | ConvertTo-Json -Depth 5 | Set-Content -Path $reportPath -Encoding UTF8
    Write-Error "Pre-release audit failed. Report: $reportPath"
    throw
}
