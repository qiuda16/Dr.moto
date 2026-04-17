param(
  [Parameter(Mandatory = $true)]
  [string]$SyncScriptPath,
  [Parameter(Mandatory = $true)]
  [string]$IncrementalArgs,
  [Parameter(Mandatory = $true)]
  [string]$FullArgs,
  [string]$IncrementalTaskName = "DrMoto-MySQL-IncrementalSync",
  [string]$FullTaskName = "DrMoto-MySQL-FullSync"
)

$ErrorActionPreference = "Stop"

$syncScriptAbs = (Resolve-Path $SyncScriptPath).Path

$incCmd = "powershell -NoProfile -ExecutionPolicy Bypass -File `"$syncScriptAbs`" $IncrementalArgs"
$fullCmd = "powershell -NoProfile -ExecutionPolicy Bypass -File `"$syncScriptAbs`" $FullArgs"

Write-Host "[INFO] Creating/Updating incremental task ($IncrementalTaskName) ..."
schtasks /Create /F /TN $IncrementalTaskName /TR $incCmd /SC MINUTE /MO 15

Write-Host "[INFO] Creating/Updating full task ($FullTaskName) ..."
schtasks /Create /F /TN $FullTaskName /TR $fullCmd /SC DAILY /ST 03:00

Write-Host "[OK] Task schedule created."
Write-Host "Check: schtasks /Query /TN $IncrementalTaskName /V /FO LIST"
Write-Host "Check: schtasks /Query /TN $FullTaskName /V /FO LIST"
