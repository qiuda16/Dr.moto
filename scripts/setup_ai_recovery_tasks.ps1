param(
  [string]$TaskName = "DrMoto-AI-Recovery-Guard",
  [string]$GuardScriptPath = "scripts/ai_recovery_guard.ps1",
  [int]$IntervalMinutes = 5,
  [string]$StoreName = "DrMoto Store",
  [string]$WebhookUrl = "",
  [string]$WebhookType = "auto",
  [switch]$UseInteractiveToken
)

$ErrorActionPreference = "Stop"

if ($IntervalMinutes -lt 1) {
  throw "IntervalMinutes must be >= 1."
}

$guardAbs = (Resolve-Path $GuardScriptPath).Path
$arg = "-NoLogo -NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$guardAbs`" -StoreName `"$StoreName`" -WebhookType `"$WebhookType`""
if (-not [string]::IsNullOrWhiteSpace($WebhookUrl)) {
  $arg += " -WebhookUrl `"$WebhookUrl`""
}

if (-not (Get-Module -ListAvailable -Name ScheduledTasks)) {
  throw "ScheduledTasks module is unavailable on this host."
}

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $arg
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes $IntervalMinutes) -RepetitionDuration (New-TimeSpan -Days 3650)
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Minutes 30) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -Hidden
if ($UseInteractiveToken) {
  $principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited
} else {
  $principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType S4U -RunLevel Limited
}

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Force | Out-Null

Write-Host "[OK] AI recovery guard task created/updated." -ForegroundColor Green
Write-Host ("Task: {0}" -f $TaskName)
Write-Host ("Command: powershell.exe {0}" -f $arg)
Write-Host ("LogonType: {0}" -f ($(if ($UseInteractiveToken) { "InteractiveToken" } else { "S4U (background)" })))
Write-Host ("Check: Get-ScheduledTask -TaskName '{0}' | Get-ScheduledTaskInfo" -f $TaskName)
