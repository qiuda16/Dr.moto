param(
  [Parameter(Mandatory = $true)]
  [string]$AppId,
  [Parameter(Mandatory = $true)]
  [string]$ApiBase
)

$ErrorActionPreference = 'Stop'

if ($AppId -notmatch '^wx[a-zA-Z0-9]{16}$') {
  throw 'AppId 格式不正确，应类似 wx1234567890abcdef'
}
if ($ApiBase -notmatch '^https://') {
  throw 'ApiBase 必须是 https:// 开头'
}

$manifestPath = 'src/manifest.json'
$envPath = '.env'

$manifest = Get-Content -Raw $manifestPath | ConvertFrom-Json
$manifest.appid = $AppId
$manifest.'mp-weixin'.appid = $AppId
$manifest | ConvertTo-Json -Depth 20 | Set-Content -Encoding UTF8 $manifestPath

"VITE_API_BASE=$ApiBase" | Set-Content -Encoding UTF8 $envPath

Write-Host '[完成] 已写入 AppID 与 API 域名配置'
Write-Host "manifest: $manifestPath"
Write-Host "env: $envPath"
