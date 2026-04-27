param(
    [string]$WorkspaceRoot = (Resolve-Path "$PSScriptRoot\..").Path,
    [string]$WebhookUrl = $env:AI_ALERT_WEBHOOK_URL,
    [string]$WebhookType = "auto",
    [string]$StoreName = "DrMoto Store"
)

$ErrorActionPreference = "Stop"

$alertScript = (Resolve-Path "$PSScriptRoot\ai_recovery_alert.ps1").Path
$recoveryScript = (Resolve-Path "$PSScriptRoot\ai_assistant_recovery.ps1").Path
$PreAlertWindowMinutes = 15
$PreAlertMaxFallbackEvents = 3
$PostAlertWindowMinutes = 3
$PostAlertMaxFallbackEvents = 999

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
    $payload = $null
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

function Run-ScriptFile {
    param([string]$Path, [string[]]$ScriptArgs = @())
    $global:LASTEXITCODE = 0
    $null = & powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File "$Path" @ScriptArgs
    $code = $global:LASTEXITCODE
    if ($null -eq $code) { return 0 }
    return [int]$code
}

function Run-AlertWithRetry {
    param(
        [string[]]$AlertArgs,
        [int]$Attempts = 4,
        [int]$SleepSeconds = 8
    )
    $last = 1
    for ($i = 0; $i -lt $Attempts; $i++) {
        $last = Run-ScriptFile -Path $alertScript -ScriptArgs $AlertArgs
        if ($last -eq 0) {
            return 0
        }
        if ($i -lt ($Attempts - 1)) {
            Write-Host ("[Guard] Alert retry {0}/{1} after warm-up..." -f ($i + 1), $Attempts) -ForegroundColor Yellow
            Start-Sleep -Seconds $SleepSeconds
        }
    }
    return $last
}

Write-Host "[Guard] Running pre-check alert..." -ForegroundColor Cyan
$preArgs = @(
    "-StoreName", $StoreName,
    "-WebhookType", $WebhookType,
    "-WindowMinutes", "$PreAlertWindowMinutes",
    "-MaxFallbackEvents", "$PreAlertMaxFallbackEvents"
)
if (-not [string]::IsNullOrWhiteSpace($WebhookUrl)) {
    $preArgs += @("-WebhookUrl", $WebhookUrl)
}
$alertExit = Run-AlertWithRetry -AlertArgs $preArgs -Attempts 2 -SleepSeconds 5
if ($alertExit -eq 0) {
    Write-Host "[Guard] Alert check pass, no action needed." -ForegroundColor Green
    exit 0
}

Write-Host "[Guard] Alert failed, starting recovery workflow..." -ForegroundColor Yellow
Send-Webhook -Url $WebhookUrl -Type $WebhookType -Message "[AI Guard][ACTION] $StoreName`nAlert failed, starting auto recovery now."

$recoveryExit = Run-ScriptFile -Path $recoveryScript
if ($recoveryExit -ne 0) {
    Send-Webhook -Url $WebhookUrl -Type $WebhookType -Message "[AI Guard][FAIL] $StoreName`nRecovery script failed with exit code $recoveryExit."
    Write-Host "[Guard] Recovery script failed." -ForegroundColor Red
    exit 3
}

Write-Host "[Guard] Running post-recovery alert..." -ForegroundColor Cyan
$postArgs = @(
    "-StoreName", $StoreName,
    "-WebhookType", $WebhookType,
    "-WindowMinutes", "$PostAlertWindowMinutes",
    "-MaxFallbackEvents", "$PostAlertMaxFallbackEvents"
)
if (-not [string]::IsNullOrWhiteSpace($WebhookUrl)) {
    $postArgs += @("-WebhookUrl", $WebhookUrl)
}
$postAlertExit = Run-AlertWithRetry -AlertArgs $postArgs -Attempts 5 -SleepSeconds 10
if ($postAlertExit -eq 0) {
    Send-Webhook -Url $WebhookUrl -Type $WebhookType -Message "[AI Guard][RECOVERED] $StoreName`nAuto recovery completed and post-check passed."
    Write-Host "[Guard] Recovery completed successfully." -ForegroundColor Green
    exit 0
}

Send-Webhook -Url $WebhookUrl -Type $WebhookType -Message "[AI Guard][CRITICAL] $StoreName`nPost-recovery alert still failing. Manual intervention required."
Write-Host "[Guard] Post-recovery check failed." -ForegroundColor Red
exit 4
