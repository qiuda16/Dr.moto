param(
    [string]$BaseUrl = "http://localhost:8080",
    [double]$Max5xxRatePercent = 2.0,
    [double]$MaxP95LatencySeconds = 1.5,
    [double]$MaxInFlightRequests = 100,
    [string]$ReportDir = "infra/reports/alerts"
)

$ErrorActionPreference = "Stop"

function Get-MetricLines {
    param([string]$Text)
    return ($Text -split "`n") | ForEach-Object { $_.Trim() } | Where-Object { $_ -and -not $_.StartsWith("#") }
}

Write-Host "[1/3] Check API health..." -ForegroundColor Cyan
$health = Invoke-RestMethod -Uri "$BaseUrl/health" -Method Get
if ($health.status -ne "ok") {
    throw "Health check failed: status=$($health.status)"
}

Write-Host "[2/3] Fetch metrics..." -ForegroundColor Cyan
$metricsRaw = Invoke-WebRequest -Uri "$BaseUrl/metrics" -Method Get
$lines = Get-MetricLines -Text $metricsRaw.Content

$requestSeries = @{}
$totalRequests = 0.0
$fiveXxRequests = 0.0

foreach ($line in $lines) {
    if ($line -match '^drmoto_http_requests_total\{.*status_code="(\d+)".*\}\s+([0-9eE\+\-\.]+)$') {
        $statusCode = [int]$Matches[1]
        $value = [double]$Matches[2]
        $totalRequests += $value
        if ($statusCode -ge 500 -and $statusCode -lt 600) {
            $fiveXxRequests += $value
        }
    }
}

$errorRate = 0.0
if ($totalRequests -gt 0) {
    $errorRate = ($fiveXxRequests / $totalRequests) * 100.0
}

$bucketTotals = @{}
$bucketCountTotal = 0.0
foreach ($line in $lines) {
    if ($line -match '^drmoto_http_request_duration_seconds_bucket\{([^}]*)\}\s+([0-9eE\+\-\.]+)$') {
        $labels = $Matches[1]
        $value = [double]$Matches[2]
        if ($labels -match 'le="([^"]+)"') {
            $le = $Matches[1]
            if (-not $bucketTotals.ContainsKey($le)) {
                $bucketTotals[$le] = 0.0
            }
            $bucketTotals[$le] += $value
        }
    } elseif ($line -match '^drmoto_http_request_duration_seconds_count\{.*\}\s+([0-9eE\+\-\.]+)$') {
        $bucketCountTotal += [double]$Matches[1]
    }
}

$p95Estimate = [double]::PositiveInfinity
$latencySamples = $bucketCountTotal
if ($bucketTotals.ContainsKey("+Inf") -and $bucketTotals["+Inf"] -gt $latencySamples) {
    $latencySamples = $bucketTotals["+Inf"]
}

if ($latencySamples -gt 0 -and $bucketTotals.Count -gt 0) {
    $orderedLe = $bucketTotals.Keys |
        Where-Object { $_ -ne "+Inf" } |
        ForEach-Object { [PSCustomObject]@{ raw = $_; value = [double]$_ } } |
        Sort-Object value
    $target = $latencySamples * 0.95
    foreach ($item in $orderedLe) {
        if ($bucketTotals[$item.raw] -ge $target) {
            $p95Estimate = $item.value
            break
        }
    }
}

$inFlight = 0.0
$inFlightLine = $lines | Where-Object { $_ -match '^drmoto_http_in_progress\s+([0-9eE\+\-\.]+)$' } | Select-Object -First 1
if ($inFlightLine -and $inFlightLine -match '^drmoto_http_in_progress\s+([0-9eE\+\-\.]+)$') {
    $inFlight = [double]$Matches[1]
}

Write-Host "[3/3] Evaluate thresholds..." -ForegroundColor Cyan
Write-Host ("5xx rate: {0:N2}% (limit {1:N2}%)" -f $errorRate, $Max5xxRatePercent)
if ([double]::IsPositiveInfinity($p95Estimate)) {
    Write-Host ("P95 latency estimate: N/A (no histogram samples yet, limit {0:N3}s)" -f $MaxP95LatencySeconds)
} else {
    Write-Host ("P95 latency estimate: {0:N3}s (limit {1:N3}s)" -f $p95Estimate, $MaxP95LatencySeconds)
}
Write-Host ("In-flight requests: {0:N0} (limit {1:N0})" -f $inFlight, $MaxInFlightRequests)

if ($errorRate -gt $Max5xxRatePercent) {
    throw "5xx rate exceeded threshold."
}
if (-not [double]::IsPositiveInfinity($p95Estimate) -and $p95Estimate -gt $MaxP95LatencySeconds) {
    throw "P95 latency exceeded threshold."
}
if ($inFlight -gt $MaxInFlightRequests) {
    throw "In-flight request threshold exceeded."
}

if (-not (Test-Path $ReportDir)) {
    New-Item -ItemType Directory -Path $ReportDir -Force | Out-Null
}
$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$reportPath = Join-Path $ReportDir ("alert_check_{0}.json" -f $ts)
$report = @{
    time = (Get-Date).ToString("o")
    base_url = $BaseUrl
    result = "pass"
    metrics = @{
        error_rate_percent = $errorRate
        p95_latency_seconds = if ([double]::IsPositiveInfinity($p95Estimate)) { $null } else { $p95Estimate }
        in_flight_requests = $inFlight
    }
    thresholds = @{
        max_5xx_rate_percent = $Max5xxRatePercent
        max_p95_latency_seconds = $MaxP95LatencySeconds
        max_in_flight_requests = $MaxInFlightRequests
    }
}
$report | ConvertTo-Json -Depth 6 | Out-File -FilePath $reportPath -Encoding utf8

Write-Host "Alert check passed." -ForegroundColor Green
Write-Host ("Report saved: {0}" -f $reportPath) -ForegroundColor Green
