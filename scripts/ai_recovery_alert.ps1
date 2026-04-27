param(
    [string]$AiBaseUrl = "http://127.0.0.1:8001",
    [int]$WindowMinutes = 15,
    [int]$MaxFallbackEvents = 3,
    [string]$ReportDir = "infra/reports/alerts",
    [string]$WebhookUrl = $env:AI_ALERT_WEBHOOK_URL,
    [string]$WebhookType = "auto",
    [string]$StoreName = "DrMoto Store"
)

$ErrorActionPreference = "Stop"

function Write-Info($text) {
    Write-Host $text -ForegroundColor Cyan
}

function Resolve-WebhookType {
    param([string]$Type, [string]$Url)
    $normalized = [string]$Type
    if ($normalized -and $normalized.ToLower() -ne "auto") { return $normalized.ToLower() }
    $target = [string]$Url
    if ($target -match "feishu|lark") { return "feishu" }
    if ($target -match "dingtalk|ding") { return "dingtalk" }
    if ($target -match "slack") { return "slack" }
    return "generic"
}

function Send-Webhook {
    param([string]$Url, [string]$Type, [string]$Message)
    if ([string]::IsNullOrWhiteSpace($Url)) { return }
    $resolved = Resolve-WebhookType -Type $Type -Url $Url
    if ($resolved -eq "feishu") {
        $payload = @{ msg_type = "text"; content = @{ text = $Message } }
    } elseif ($resolved -eq "dingtalk") {
        $payload = @{ msgtype = "text"; text = @{ content = $Message } }
    } elseif ($resolved -eq "slack") {
        $payload = @{ text = $Message }
    } else {
        $payload = @{ message = $Message }
    }
    try {
        Invoke-RestMethod -Method Post -Uri $Url -ContentType "application/json" -Body ($payload | ConvertTo-Json -Depth 6) -TimeoutSec 8 | Out-Null
    } catch {
        Write-Host ("Webhook send failed: {0}" -f $_.Exception.Message) -ForegroundColor Yellow
    }
}

function Safe-GetJson {
    param([string]$Url, [int]$TimeoutSec = 8, [int]$Attempts = 3)
    $lastErr = ""
    for ($i = 0; $i -lt $Attempts; $i++) {
        try {
            $data = Invoke-RestMethod -Method Get -Uri $Url -TimeoutSec $TimeoutSec
            return @{ ok = $true; data = $data; error = "" }
        } catch {
            $lastErr = $_.Exception.Message
            if ($i -lt ($Attempts - 1)) {
                Start-Sleep -Seconds (2 + $i)
            }
        }
    }
    return @{ ok = $false; data = $null; error = $lastErr }
}

Write-Info "[1/3] Reading AI deep health..."
$deepRes = Safe-GetJson -Url "$AiBaseUrl/health/deep" -TimeoutSec 8 -Attempts 3

Write-Info "[2/3] Reading recovery events..."
$eventsRes = Safe-GetJson -Url "$AiBaseUrl/health/recovery-events?minutes=$WindowMinutes" -TimeoutSec 8 -Attempts 3

Write-Info "[3/3] Evaluating thresholds..."
$violations = @()
$fallbackCount = 0
$bffStatus = "unknown"
$ollamaStatus = "unknown"
$memoryStatus = "unknown"
$forcedRecovery = $false

if (-not $deepRes.ok) {
    $violations += "deep_health_unreachable"
} else {
    $deep = $deepRes.data
    $bffStatus = [string]$deep.checks.bff.status
    $ollamaStatus = [string]$deep.checks.ollama.status
    $memoryStatus = [string]$deep.checks.memory.status
    $forcedRecovery = [bool]$deep.recovery_mode_forced
    if ($bffStatus -ne "ok") { $violations += "bff_not_ok" }
    if ($ollamaStatus -ne "ok") { $violations += "ollama_not_ok" }
    if ($memoryStatus -ne "ok") { $violations += "memory_not_ok" }
    if ($forcedRecovery) { $violations += "forced_recovery_mode_on" }
}

if (-not $eventsRes.ok) {
    $violations += "recovery_events_unreachable"
} else {
    $events = $eventsRes.data
    if ($events.counts -and $events.counts.llm_fallback_triggered) {
        $fallbackCount = [int]$events.counts.llm_fallback_triggered
    }
    if ($fallbackCount -gt $MaxFallbackEvents) { $violations += "fallback_events_exceeded" }
}

Write-Host ("BFF={0} Ollama={1} Memory={2} ForcedRecovery={3}" -f $bffStatus, $ollamaStatus, $memoryStatus, $forcedRecovery)
Write-Host ("Fallback events in {0}m: {1} (limit {2})" -f $WindowMinutes, $fallbackCount, $MaxFallbackEvents)

if (-not (Test-Path $ReportDir)) {
    New-Item -ItemType Directory -Path $ReportDir -Force | Out-Null
}
$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$reportPath = Join-Path $ReportDir ("ai_recovery_alert_{0}.json" -f $ts)
$report = @{
    time = (Get-Date).ToString("o")
    ai_base_url = $AiBaseUrl
    window_minutes = $WindowMinutes
    status = if ($violations.Count -eq 0) { "pass" } else { "fail" }
    checks = @{
        bff = $bffStatus
        ollama = $ollamaStatus
        memory = $memoryStatus
        forced_recovery_mode = $forcedRecovery
        fallback_events = $fallbackCount
        max_fallback_events = $MaxFallbackEvents
        deep_error = $deepRes.error
        events_error = $eventsRes.error
    }
    violations = $violations
}
$report | ConvertTo-Json -Depth 8 | Out-File -FilePath $reportPath -Encoding utf8

if ($violations.Count -gt 0) {
    Write-Host ("AI recovery alert failed: {0}" -f ($violations -join ",")) -ForegroundColor Red
    Write-Host ("Report saved: {0}" -f $reportPath) -ForegroundColor Yellow
    $msg = "[AI Alert][FAIL] $StoreName`nViolations: $($violations -join ',')`nFallbackEvents($WindowMinutes m): $fallbackCount`nReport: $reportPath"
    Send-Webhook -Url $WebhookUrl -Type $WebhookType -Message $msg
    exit 2
}

Write-Host "AI recovery alert passed." -ForegroundColor Green
Write-Host ("Report saved: {0}" -f $reportPath) -ForegroundColor Green
$msg = "[AI Alert][PASS] $StoreName`nDeepHealth: ok`nFallbackEvents($WindowMinutes m): $fallbackCount`nReport: $reportPath"
Send-Webhook -Url $WebhookUrl -Type $WebhookType -Message $msg
