param(
  [Parameter(Mandatory = $true)]
  [string]$DatabaseUrl,
  [Parameter(Mandatory = $false)]
  [string]$EnvFile = "infra/.env"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $EnvFile)) {
  throw "Env file not found: $EnvFile"
}

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backup = "$EnvFile.bak.$timestamp"
Copy-Item $EnvFile $backup -Force
Write-Host "[OK] Backup created: $backup"

$lines = Get-Content $EnvFile
$found = $false
for ($i = 0; $i -lt $lines.Count; $i++) {
  if ($lines[$i] -match '^BFF_DATABASE_URL=') {
    $lines[$i] = "BFF_DATABASE_URL=$DatabaseUrl"
    $found = $true
    break
  }
}
if (-not $found) {
  $lines += "BFF_DATABASE_URL=$DatabaseUrl"
}
Set-Content -Path $EnvFile -Value $lines -Encoding UTF8
Write-Host "[OK] Updated BFF_DATABASE_URL in $EnvFile"

Push-Location infra
try {
  docker compose --env-file .env up -d bff | Out-Host
} finally {
  Pop-Location
}

$healthOk = $false
for ($j = 0; $j -lt 30; $j++) {
  Start-Sleep -Seconds 2
  try {
    $resp = Invoke-RestMethod -Method Get -Uri "http://localhost:18080/health" -TimeoutSec 2
    if ($resp.status -eq "ok") {
      $healthOk = $true
      break
    }
  } catch {
  }
}

if (-not $healthOk) {
  throw "BFF health check failed after switch."
}

Write-Host "[OK] BFF restarted and healthy."

powershell -ExecutionPolicy Bypass -File scripts\verify_customer_db_readonly.ps1 | Out-Host
