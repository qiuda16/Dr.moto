param(
    [string]$BffBaseUrl = "http://127.0.0.1:18080",
    [string]$AiBaseUrl = "http://127.0.0.1:8001",
    [string]$AdminUser = "admin",
    [string]$AdminPassword = "change_me_now",
    [string]$ComposeFile = "infra/docker-compose.yml"
)

$ErrorActionPreference = "Stop"

function Write-Step($text) {
    Write-Host $text -ForegroundColor Cyan
}

function Test-AiHealth {
    try {
        $basic = Invoke-RestMethod -Method Get -Uri "$AiBaseUrl/health" -TimeoutSec 8
        $deep = Invoke-RestMethod -Method Get -Uri "$AiBaseUrl/health/deep" -TimeoutSec 10
        return @{ basic = $basic; deep = $deep }
    } catch {
        return @{
            basic = @{ status = "down" }
            deep = @{ status = "degraded"; checks = @{ bff = @{ status = "down" }; ollama = @{ status = "down" }; memory = @{ status = "down" }; kb = @{ status = "unknown"; json_file_count = 0 } } }
        }
    }
}

function Get-BffToken {
    $form = "username=$AdminUser&password=$AdminPassword"
    $resp = Invoke-RestMethod -Method Post -Uri "$BffBaseUrl/auth/token" -ContentType "application/x-www-form-urlencoded" -Body $form -TimeoutSec 10
    return $resp.access_token
}

function Invoke-AiScenario {
    param([string]$Token, [string]$Query)
    $headers = @{ Authorization = "Bearer $Token" }
    $body = @{ message = $Query; context = @{} } | ConvertTo-Json
    $resp = Invoke-RestMethod -Method Post -Uri "$BffBaseUrl/ai/assistant/chat" -Headers $headers -ContentType "application/json" -Body $body -TimeoutSec 120
    $answer = [string]($resp.response)
    return @{ query = $Query; ok = -not [string]::IsNullOrWhiteSpace($answer); answer = $answer }
}

function Run-ScenarioMatrix {
    param([string]$Token)
    $queries = @(
        "which license plates are ready for delivery now",
        "what bmw models are in the system",
        "motorcycle rear brake noise first check steps",
        "is oil filter in stock now",
        "what is current status of this work order",
        "remember plate 京A12345 and then tell me the plate"
    )
    $rows = @()
    foreach ($q in $queries) {
        $rows += Invoke-AiScenario -Token $Token -Query $q
    }
    return $rows
}

function Try-ScenarioMatrix {
    try {
        $token = Get-BffToken
        $rows = Run-ScenarioMatrix -Token $token
        $passCount = ($rows | Where-Object { $_.ok }).Count
        return @{
            success = ($passCount -eq $rows.Count)
            rows = @($rows)
            pass = $passCount
            total = $rows.Count
            error = ""
        }
    } catch {
        return @{
            success = $false
            rows = @()
            pass = 0
            total = 0
            error = $_.Exception.Message
        }
    }
}

function Restart-Services {
    param([string[]]$Services)
    foreach ($svc in $Services) {
        Write-Host ("Restarting service: {0}" -f $svc) -ForegroundColor Yellow
        docker compose -f $ComposeFile restart $svc | Out-Null
    }
    Start-Sleep -Seconds 6
}

function Build-Report {
    param([hashtable]$Health, [array]$Rows, [string]$Stage, [string[]]$Notes)
    $okCount = ($Rows | Where-Object { $_.ok }).Count
    $total = $Rows.Count
    $ts = Get-Date -Format "yyyyMMdd_HHmmss"
    $dir = "docs/recovery_reports"
    New-Item -ItemType Directory -Path $dir -Force | Out-Null
    $file = Join-Path $dir ("ai_recovery_{0}.md" -f $ts)

    $lines = @()
    $lines += "# AI Assistant Recovery Report"
    $lines += ""
    $lines += ("Generated at: {0}" -f (Get-Date).ToString("yyyy-MM-dd HH:mm:ss"))
    $lines += ("Stage: {0}" -f $Stage)
    $lines += ("AI Basic Health: {0}" -f ($Health.basic.status))
    $lines += ("AI Deep Health: {0}" -f ($Health.deep.status))
    $lines += ("Scenario Pass: {0}/{1}" -f $okCount, $total)
    $lines += ""
    $lines += "## Deep Checks"
    $lines += ("- BFF: {0}" -f ($Health.deep.checks.bff.status))
    $lines += ("- Ollama: {0}" -f ($Health.deep.checks.ollama.status))
    $lines += ("- Memory: {0}" -f ($Health.deep.checks.memory.status))
    $lines += ("- KB: {0} ({1})" -f ($Health.deep.checks.kb.status), ($Health.deep.checks.kb.json_file_count))
    if ($Notes -and $Notes.Count -gt 0) {
        $lines += ""
        $lines += "## Recovery Notes"
        foreach ($n in $Notes) {
            $lines += ("- {0}" -f $n)
        }
    }
    $lines += ""
    $lines += "## Scenario Results"
    foreach ($row in $Rows) {
        $lines += ("- Q: {0}" -f $row.query)
        $lines += ("  - OK: {0}" -f $row.ok)
        $lines += ("  - A: {0}" -f $row.answer)
    }
    Set-Content -Path $file -Value ($lines -join "`r`n") -Encoding UTF8
    return $file
}

$notes = New-Object System.Collections.Generic.List[string]

Write-Step "[1/5] Checking AI health..."
$health = Test-AiHealth

Write-Step "[2/5] Running scenario probe..."
$probe = Try-ScenarioMatrix
$rows = @($probe.rows)
$needRecovery = -not $probe.success
$stage = "initial"
if ($probe.error) {
    $notes.Add("Initial probe error: $($probe.error)")
    Write-Host ("Initial probe failed: {0}" -f $probe.error) -ForegroundColor Yellow
}

if ($needRecovery) {
    Write-Step "[3/5] Recovery stage A: restart ai"
    Restart-Services -Services @("ai")
    $health = Test-AiHealth
    $probe = Try-ScenarioMatrix
    $rows = @($probe.rows)
    $needRecovery = -not $probe.success
    $stage = "after_restart_ai"
    if ($probe.error) {
        $notes.Add("Stage A probe error: $($probe.error)")
    }
}

if ($needRecovery) {
    Write-Step "[4/5] Recovery stage B: restart bff + ai"
    Restart-Services -Services @("bff", "ai")
    $health = Test-AiHealth
    $probe = Try-ScenarioMatrix
    $rows = @($probe.rows)
    $needRecovery = -not $probe.success
    $stage = "after_restart_bff_ai"
    if ($probe.error) {
        $notes.Add("Stage B probe error: $($probe.error)")
    }
}

if ($needRecovery) {
    Write-Step "[4/5] Recovery stage C: restart redis + bff + ai"
    Restart-Services -Services @("redis", "bff", "ai")
    $health = Test-AiHealth
    $probe = Try-ScenarioMatrix
    $rows = @($probe.rows)
    $needRecovery = -not $probe.success
    $stage = "after_restart_redis_bff_ai"
    if ($probe.error) {
        $notes.Add("Stage C probe error: $($probe.error)")
    }
}

Write-Step "[5/5] Writing recovery report..."
$reportFile = Build-Report -Health $health -Rows $rows -Stage $stage -Notes @($notes)
Write-Host ("Recovery report: {0}" -f $reportFile) -ForegroundColor Green

if ($needRecovery) {
    Write-Host "Recovery ended with remaining failures." -ForegroundColor Red
    exit 2
}
