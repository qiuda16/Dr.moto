param(
  [Parameter(Mandatory = $true)]
  [string]$ApiBaseDomain
)

$ErrorActionPreference = 'Continue'

Write-Host "[检查] 接口健康: $ApiBaseDomain/health"
try {
  $resp = Invoke-WebRequest -UseBasicParsing "$ApiBaseDomain/health" -TimeoutSec 8
  Write-Host "[通过] 健康检查: $($resp.StatusCode)"
} catch {
  Write-Host "[失败] 接口健康检查未通过: $($_.Exception.Message)"
}

Write-Host "[检查] HTTPS 协议"
if ($ApiBaseDomain -match '^https://') {
  Write-Host '[通过] 已使用 HTTPS'
} else {
  Write-Host '[失败] 必须使用 HTTPS 域名'
}

Write-Host "[检查] 生产环境建议项（人工确认）"
Write-Host '1) 微信公众平台已配置 request 合法域名'
Write-Host '2) BFF 已配置 BFF_WECHAT_APP_ID / BFF_WECHAT_APP_SECRET'
Write-Host '3) BFF_ENABLE_DEV_ENDPOINTS=false'
Write-Host '4) BFF_ENABLE_MOCK_PAYMENT=false'
Write-Host '5) 已完成隐私政策与用户协议页面'
