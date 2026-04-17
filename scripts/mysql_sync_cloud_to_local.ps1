param(
  [Parameter(Mandatory = $true)]
  [string]$SourceHost,
  [int]$SourcePort = 3306,
  [Parameter(Mandatory = $true)]
  [string]$SourceUser,
  [Parameter(Mandatory = $true)]
  [string]$SourcePassword,
  [Parameter(Mandatory = $true)]
  [string]$SourceDatabase,

  [Parameter(Mandatory = $true)]
  [string]$TargetHost,
  [int]$TargetPort = 3306,
  [Parameter(Mandatory = $true)]
  [string]$TargetUser,
  [Parameter(Mandatory = $true)]
  [string]$TargetPassword,
  [Parameter(Mandatory = $true)]
  [string]$TargetDatabase,

  [ValidateSet("incremental", "full")]
  [string]$Mode = "incremental",
  [string]$StateFile = "infra/backups/mysql_sync_state.json",
  [string]$WorkDir = "infra/backups/mysql_sync",
  [string[]]$TableAllowList = @(),
  [int]$DefaultLookbackMinutes = 60
)

$ErrorActionPreference = "Stop"

function Require-Command([string]$name) {
  if (-not (Get-Command $name -ErrorAction SilentlyContinue)) {
    throw "Missing command: $name. Please install MySQL client tools."
  }
}

function Invoke-MySqlQuery([string]$host, [int]$port, [string]$user, [string]$password, [string]$db, [string]$query) {
  $old = $env:MYSQL_PWD
  try {
    $env:MYSQL_PWD = $password
    $args = @("-h", $host, "-P", "$port", "-u", $user, "-N", "-B", "-D", $db, "-e", $query)
    $output = & mysql.exe @args
    if ($LASTEXITCODE -ne 0) {
      throw "mysql query failed: $query"
    }
    return @($output)
  } finally {
    $env:MYSQL_PWD = $old
  }
}

function Invoke-MySqlImport([string]$host, [int]$port, [string]$user, [string]$password, [string]$db, [string]$sqlFile) {
  $old = $env:MYSQL_PWD
  try {
    $env:MYSQL_PWD = $password
    & cmd.exe /c "mysql -h $host -P $port -u $user $db < `"$sqlFile`""
    if ($LASTEXITCODE -ne 0) {
      throw "mysql import failed: $sqlFile"
    }
  } finally {
    $env:MYSQL_PWD = $old
  }
}

function Invoke-MySqlDump([string[]]$extraArgs) {
  & mysqldump.exe @extraArgs
  if ($LASTEXITCODE -ne 0) {
    throw "mysqldump failed."
  }
}

Require-Command "mysql.exe"
Require-Command "mysqldump.exe"

New-Item -ItemType Directory -Path $WorkDir -Force | Out-Null
New-Item -ItemType Directory -Path (Split-Path -Parent $StateFile) -Force | Out-Null

$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$tmpSql = Join-Path $WorkDir "sync_$stamp.sql"

if ($Mode -eq "full") {
  Write-Host "[FULL] Export source database..."
  $old = $env:MYSQL_PWD
  try {
    $env:MYSQL_PWD = $SourcePassword
    $dumpArgs = @(
      "-h", $SourceHost, "-P", "$SourcePort", "-u", $SourceUser,
      "--single-transaction",
      "--set-gtid-purged=OFF",
      "--default-character-set=utf8mb4",
      "--routines", "--triggers", "--events",
      $SourceDatabase
    )
    $content = & mysqldump.exe @dumpArgs
    if ($LASTEXITCODE -ne 0) {
      throw "mysqldump full failed"
    }
    $content | Out-File -FilePath $tmpSql -Encoding utf8
  } finally {
    $env:MYSQL_PWD = $old
  }

  Write-Host "[FULL] Import to target..."
  Invoke-MySqlImport -host $TargetHost -port $TargetPort -user $TargetUser -password $TargetPassword -db $TargetDatabase -sqlFile $tmpSql

  $state = @{
    last_sync_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-dd HH:mm:ss")
    mode = "full"
  }
  $state | ConvertTo-Json | Out-File -FilePath $StateFile -Encoding utf8
  Remove-Item -LiteralPath $tmpSql -Force -ErrorAction SilentlyContinue
  Write-Host "[OK] Full sync finished."
  exit 0
}

# Incremental mode
$lastSyncUtc = $null
if (Test-Path $StateFile) {
  try {
    $obj = Get-Content -Raw -Path $StateFile | ConvertFrom-Json
    $lastSyncUtc = [DateTime]::Parse($obj.last_sync_utc).ToUniversalTime()
  } catch {
    $lastSyncUtc = $null
  }
}
if (-not $lastSyncUtc) {
  $lastSyncUtc = (Get-Date).ToUniversalTime().AddMinutes(-1 * [Math]::Abs($DefaultLookbackMinutes))
}
$lastMark = $lastSyncUtc.ToString("yyyy-MM-dd HH:mm:ss")
Write-Host "[INCREMENTAL] Last watermark UTC: $lastMark"

if ($TableAllowList.Count -eq 0) {
  $tables = Invoke-MySqlQuery -host $SourceHost -port $SourcePort -user $SourceUser -password $SourcePassword -db $SourceDatabase -query "SHOW TABLES;"
} else {
  $tables = $TableAllowList
}

$merged = New-Object System.Collections.Generic.List[string]
$eligibleCount = 0

foreach ($table in $tables) {
  if (-not $table) { continue }
  $escaped = $table.Replace("'", "''")
  $columnRows = Invoke-MySqlQuery -host $SourceHost -port $SourcePort -user $SourceUser -password $SourcePassword -db "information_schema" -query "SELECT COLUMN_NAME FROM COLUMNS WHERE TABLE_SCHEMA='$SourceDatabase' AND TABLE_NAME='$escaped' AND COLUMN_NAME IN ('updated_at','create_date','created_at');"
  if (-not $columnRows -or $columnRows.Count -eq 0) {
    continue
  }

  $conditions = New-Object System.Collections.Generic.List[string]
  foreach ($c in $columnRows) {
    if ($c -eq "updated_at") { $conditions.Add("`$c >= '$lastMark'") }
    if ($c -eq "created_at") { $conditions.Add("`$c >= '$lastMark'") }
    if ($c -eq "create_date") { $conditions.Add("`$c >= '$lastMark'") }
  }
  if ($conditions.Count -eq 0) { continue }
  $where = "(" + ($conditions -join " OR ") + ")"

  Write-Host "[INCREMENTAL] Dump table: $table where $where"
  $old = $env:MYSQL_PWD
  try {
    $env:MYSQL_PWD = $SourcePassword
    $dumpArgs = @(
      "-h", $SourceHost, "-P", "$SourcePort", "-u", $SourceUser,
      "--set-gtid-purged=OFF",
      "--default-character-set=utf8mb4",
      "--no-create-info",
      "--skip-triggers",
      "--replace",
      "--where=$where",
      $SourceDatabase,
      $table
    )
    $rows = & mysqldump.exe @dumpArgs
    if ($LASTEXITCODE -ne 0) {
      throw "mysqldump incremental failed on table $table"
    }
    foreach ($line in $rows) {
      $merged.Add($line)
    }
    $eligibleCount += 1
  } finally {
    $env:MYSQL_PWD = $old
  }
}

if ($merged.Count -gt 0) {
  $merged | Out-File -FilePath $tmpSql -Encoding utf8
  Write-Host "[INCREMENTAL] Import merged changes..."
  Invoke-MySqlImport -host $TargetHost -port $TargetPort -user $TargetUser -password $TargetPassword -db $TargetDatabase -sqlFile $tmpSql
  Remove-Item -LiteralPath $tmpSql -Force -ErrorAction SilentlyContinue
} else {
  Write-Host "[INCREMENTAL] No changed rows found."
}

$state = @{
  last_sync_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-dd HH:mm:ss")
  mode = "incremental"
  scanned_tables = $tables.Count
  eligible_tables = $eligibleCount
}
$state | ConvertTo-Json | Out-File -FilePath $StateFile -Encoding utf8
Write-Host "[OK] Incremental sync finished."
