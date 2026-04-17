param(
  [Parameter(Mandatory = $false)]
  [string]$ProjectRoot = "clients/mp_customer_uni"
)

$ErrorActionPreference = 'Continue'
$fail = $false

function Pass($msg) { Write-Host "[通过] $msg" }
function Fail($msg) { Write-Host "[失败] $msg"; $script:fail = $true }
function Warn($msg) { Write-Host "[提示] $msg" }

$manifestPath = Join-Path $ProjectRoot 'src/manifest.json'
$envPath = Join-Path $ProjectRoot '.env'
$buildPath = Join-Path $ProjectRoot 'dist/build/mp-weixin'

if (!(Test-Path $manifestPath)) {
  Fail "manifest.json 不存在：$manifestPath"
} else {
  $manifest = Get-Content -Raw $manifestPath | ConvertFrom-Json
  $appid = [string]$manifest.appid
  $mpAppid = [string]$manifest.'mp-weixin'.appid
  if ($appid -match '^wx[a-zA-Z0-9]{16}$' -and $mpAppid -eq $appid) {
    Pass "AppID 已配置且主/微信配置一致"
  } else {
    Fail "AppID 未正确配置，请运行 prepare_release.ps1"
  }
}

if (!(Test-Path $envPath)) {
  Fail ".env 不存在：$envPath"
} else {
  $envContent = Get-Content -Raw $envPath
  if ($envContent -match 'VITE_API_BASE=(.+)') {
    $apiBase = $matches[1].Trim()
    if ($apiBase -match '^https://') {
      Pass "VITE_API_BASE 已配置为 HTTPS"
      try {
        $resp = Invoke-WebRequest -UseBasicParsing "$apiBase/health" -TimeoutSec 8
        if ($resp.StatusCode -eq 200) { Pass "后端健康检查通过 ($apiBase/health)" }
        else { Warn "健康检查返回码：$($resp.StatusCode)" }
      } catch {
        Warn "无法访问 $apiBase/health：$($_.Exception.Message)"
      }
    } else {
      Fail "VITE_API_BASE 必须使用 HTTPS"
    }
  } else {
    Fail "缺少 VITE_API_BASE 配置"
  }
}

if (Test-Path $buildPath) {
  Pass "已存在微信构建产物：$buildPath"
} else {
  Warn "尚未构建微信包，请执行 npm run build:mp-weixin"
}

$requiredPages = @(
  'src/pages/privacy/index.vue',
  'src/pages/agreement/index.vue',
  'src/pages/auth/login.vue'
)
foreach ($p in $requiredPages) {
  $fp = Join-Path $ProjectRoot $p
  if (Test-Path $fp) { Pass "存在页面：$p" } else { Fail "缺少页面：$p" }
}

if ($fail) {
  Write-Host "`n结果：存在未通过项，请先修复后再提审。"
  exit 1
}

Write-Host "`n结果：检查通过，可以进入微信开发者工具上传版本。"
exit 0
