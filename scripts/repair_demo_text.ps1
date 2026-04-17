$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptDir
$odooSql = Join-Path $scriptDir "repair_demo_text_odoo.sql"
$bffSql = Join-Path $scriptDir "repair_demo_text_bff.sql"

Push-Location $repoRoot
try {
  $tmpOdoo = Join-Path $env:TEMP "repair_demo_text_odoo.sql"
  $tmpBff = Join-Path $env:TEMP "repair_demo_text_bff.sql"
  Copy-Item -LiteralPath $odooSql -Destination $tmpOdoo -Force
  Copy-Item -LiteralPath $bffSql -Destination $tmpBff -Force

  docker cp $tmpOdoo infra-db-1:/tmp/repair_demo_text_odoo.sql | Out-Null
  docker cp $tmpBff infra-db-1:/tmp/repair_demo_text_bff.sql | Out-Null

  Write-Host "Updating Odoo demo partner data..."
  docker exec infra-db-1 psql -U odoo -d odoo -f /tmp/repair_demo_text_odoo.sql

  Write-Host "Updating BFF demo work order data..."
  docker exec infra-db-1 psql -U odoo -d bff -f /tmp/repair_demo_text_bff.sql

  Write-Host "Demo text repair complete."
}
finally {
  Remove-Item -LiteralPath $tmpOdoo -ErrorAction SilentlyContinue
  Remove-Item -LiteralPath $tmpBff -ErrorAction SilentlyContinue
  Pop-Location
}
