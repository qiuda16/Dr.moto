param(
    [string]$ComposeFile = "infra/docker-compose.yml",
    [string]$BaseUrl = "http://localhost:8080",
    [int]$FailureDurationSeconds = 20,
    [int]$RecoveryTimeoutSeconds = 300
)

$ErrorActionPreference = "Stop"
$pollSeconds = 5

function Wait-Ready {
    param(
        [string]$Url,
        [int]$TimeoutSeconds
    )
    $start = Get-Date
    while (((Get-Date) - $start).TotalSeconds -lt $TimeoutSeconds) {
        try {
            $ready = Invoke-RestMethod -Uri "$Url/health/ready" -Method Get -TimeoutSec 5
            if ($ready.status -eq "ready") {
                return [int]((Get-Date) - $start).TotalSeconds
            }
        } catch {
            Start-Sleep -Seconds $pollSeconds
            continue
        }
        Start-Sleep -Seconds $pollSeconds
    }
    throw "Readiness did not recover within $TimeoutSeconds seconds."
}

function Wait-Degraded {
    param(
        [string]$Url,
        [int]$TimeoutSeconds
    )
    $start = Get-Date
    while (((Get-Date) - $start).TotalSeconds -lt $TimeoutSeconds) {
        try {
            $health = Invoke-RestMethod -Uri "$Url/health" -Method Get -TimeoutSec 5
            if ($health.status -ne "ok") {
                return [int]((Get-Date) - $start).TotalSeconds
            }
        } catch {
            return [int]((Get-Date) - $start).TotalSeconds
        }
        Start-Sleep -Seconds $pollSeconds
    }
    throw "Service did not degrade within $TimeoutSeconds seconds after fault injection."
}

Write-Host "[1/5] Baseline health check..." -ForegroundColor Cyan
$baseline = Invoke-RestMethod -Uri "$BaseUrl/health" -Method Get
if ($baseline.status -ne "ok") {
    throw "Baseline health is not ok."
}

Write-Host "[2/5] Inject failure: stop Odoo..." -ForegroundColor Yellow
docker compose -f $ComposeFile stop odoo

try {
    Write-Host "[3/5] Verify degradation and keep failure for $FailureDurationSeconds seconds..." -ForegroundColor Yellow
    $degradeSeconds = Wait-Degraded -Url $BaseUrl -TimeoutSeconds 120
    Write-Host ("Service degraded after {0}s" -f $degradeSeconds) -ForegroundColor Yellow
    Start-Sleep -Seconds $FailureDurationSeconds
} finally {
    Write-Host "[4/5] Recover service: start Odoo..." -ForegroundColor Cyan
    docker compose -f $ComposeFile up -d odoo
}

Write-Host "[5/5] Wait for readiness recovery..." -ForegroundColor Cyan
$recoverySeconds = Wait-Ready -Url $BaseUrl -TimeoutSeconds $RecoveryTimeoutSeconds

Write-Host ("Failure drill passed. Recovery time: {0}s" -f $recoverySeconds) -ForegroundColor Green
