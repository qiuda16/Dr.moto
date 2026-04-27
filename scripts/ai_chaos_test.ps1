param(
    [string]$ComposeFile = "infra/docker-compose.yml",
    [string]$BffBaseUrl = "http://127.0.0.1:18080",
    [string]$AiBaseUrl = "http://127.0.0.1:8001"
)

$ErrorActionPreference = "Stop"

function Step($text) {
    Write-Host $text -ForegroundColor Cyan
}

function Login-Token {
    $lastErr = $null
    for ($i = 0; $i -lt 6; $i++) {
        try {
            $resp = Invoke-RestMethod -Method Post -Uri "$BffBaseUrl/auth/token" -ContentType "application/x-www-form-urlencoded" -Body "username=admin&password=change_me_now" -TimeoutSec 15
            return $resp.access_token
        } catch {
            $lastErr = $_
            Start-Sleep -Seconds (2 + $i)
        }
    }
    return $null
}

function Ask-Bff {
    param([string]$Token, [string]$Message, [int]$TimeoutSec = 60)
    $headers = @{ Authorization = "Bearer $Token" }
    $body = @{ message = $Message; context = @{} } | ConvertTo-Json
    return Invoke-RestMethod -Method Post -Uri "$BffBaseUrl/ai/assistant/chat" -Headers $headers -ContentType "application/json" -Body $body -TimeoutSec $TimeoutSec
}

function Set-ComposeEnvAndUp {
    param([hashtable]$Env)
    $backup = @{}
    foreach ($k in $Env.Keys) {
        $backup[$k] = [Environment]::GetEnvironmentVariable($k, "Process")
        [Environment]::SetEnvironmentVariable($k, [string]$Env[$k], "Process")
    }
    try {
        docker compose -f $ComposeFile up -d ai | Out-Null
    } finally {
        foreach ($k in $Env.Keys) {
            [Environment]::SetEnvironmentVariable($k, $backup[$k], "Process")
        }
    }
    Start-Sleep -Seconds 8
}

function Restore-NormalAi {
    Set-ComposeEnvAndUp -Env @{ OLLAMA_BASE_URL = "http://host.docker.internal:11434"; AI_RECOVERY_MODE = "false" }
}

$results = @()
$queries = @(
    "which license plates are ready for delivery now",
    "what bmw models are in the system",
    "motorcycle rear brake noise first check steps",
    "help me check"
)

Step "[0/6] Baseline check"
$token = Login-Token
foreach ($q in $queries) {
    $ok = $false
    $dbg = $null
    try {
        $r = Ask-Bff -Token $token -Message $q
        $ok = [bool]($r.response)
        $dbg = $r.debug
    } catch {
        $ok = $false
        $dbg = @{ error = $_.Exception.Message }
    }
    $results += @{ phase = "baseline"; query = $q; ok = $ok; debug = $dbg }
}

Step "[1/6] Inject ollama unreachable"
Set-ComposeEnvAndUp -Env @{ OLLAMA_BASE_URL = "http://127.0.0.1:59999"; AI_RECOVERY_MODE = "false" }
$token = Login-Token
foreach ($q in $queries) {
    $ok = $false
    $dbg = $null
    try {
        $r = Ask-Bff -Token $token -Message $q
        $ok = [bool]($r.response)
        $dbg = $r.debug
    } catch {
        $ok = $false
        $dbg = @{ error = $_.Exception.Message }
    }
    $results += @{ phase = "ollama_down"; query = $q; ok = $ok; debug = $dbg }
}

Step "[2/6] Inject forced recovery mode"
Set-ComposeEnvAndUp -Env @{ OLLAMA_BASE_URL = "http://host.docker.internal:11434"; AI_RECOVERY_MODE = "true" }
$token = Login-Token
$ok = $false
$dbg = $null
try {
    $r = Ask-Bff -Token $token -Message "which license plates are ready for delivery now"
    $ok = [bool]($r.response)
    $dbg = $r.debug
} catch {
    $ok = $false
    $dbg = @{ error = $_.Exception.Message }
}
$results += @{ phase = "forced_recovery_mode"; query = "ready_plates"; ok = $ok; debug = $dbg }

Step "[3/6] Restore normal AI"
Restore-NormalAi
$token = Login-Token
$ok = $false
$dbg = $null
try {
    $r = Ask-Bff -Token $token -Message "what bmw models are in the system"
    $ok = [bool]($r.response)
    $dbg = $r.debug
} catch {
    $ok = $false
    $dbg = @{ error = $_.Exception.Message }
}
$results += @{ phase = "after_restore"; query = "bmw_models"; ok = $ok; debug = $dbg }

Step "[4/6] Inject redis stop"
docker compose -f $ComposeFile stop redis | Out-Null
Start-Sleep -Seconds 4
$ok = $false
$dbg = $null
try {
    $token = Login-Token
    $r = Ask-Bff -Token $token -Message "remember plate BJ12345 and then tell me the plate"
    $ok = [bool]($r.response)
    $dbg = $r.debug
} catch {
    $ok = $false
    $dbg = @{ error = $_.Exception.Message }
} finally {
    docker compose -f $ComposeFile up -d redis | Out-Null
    Start-Sleep -Seconds 6
}
$results += @{ phase = "redis_down"; query = "memory_query"; ok = $ok; debug = $dbg }

Step "[5/6] Inject bff stop and run guard recovery"
docker compose -f $ComposeFile stop bff | Out-Null
Start-Sleep -Seconds 3
$guardOk = $false
try {
    & powershell -NoProfile -ExecutionPolicy Bypass -File "$PSScriptRoot\ai_recovery_guard.ps1"
    $guardOk = ($LASTEXITCODE -eq 0)
} catch {
    $guardOk = $false
}
$results += @{ phase = "bff_down_guard"; query = "guard_recover"; ok = $guardOk; debug = @{ exit_code = $LASTEXITCODE } }

Step "[6/6] Final restore and report"
docker compose -f $ComposeFile up -d bff redis ai | Out-Null
Start-Sleep -Seconds 10

$pass = ($results | Where-Object { $_.ok }).Count
$total = $results.Count
$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$dir = "docs/recovery_reports"
New-Item -ItemType Directory -Path $dir -Force | Out-Null
$out = Join-Path $dir ("ai_chaos_test_{0}.json" -f $ts)
$report = @{
    time = (Get-Date).ToString("o")
    summary = @{ total = $total; pass = $pass; fail = ($total - $pass) }
    results = $results
}
$report | ConvertTo-Json -Depth 10 | Out-File -FilePath $out -Encoding utf8

Write-Host ("Chaos report: {0}" -f $out) -ForegroundColor Green
if ($pass -lt $total) { exit 2 }
