param(
    [string]$BaseUrl = "http://localhost:8080",
    [string]$Phone,
    [string]$PlateNo,
    [string]$StoreId = "default",
    [string]$MockCode = "preflight-code-001"
)

$ErrorActionPreference = "Stop"

if (-not $Phone) {
    throw "Phone is required. Example: -Phone 13800138000"
}
if (-not $PlateNo) {
    throw "PlateNo is required. Example: -PlateNo 沪A12345"
}

Write-Host "[1/6] MP customer wechat-login..." -ForegroundColor Cyan
$loginReq = @{
    code = $MockCode
    store_id = $StoreId
} | ConvertTo-Json
$loginResp = Invoke-RestMethod -Uri "$BaseUrl/mp/customer/auth/wechat-login" -Method Post -ContentType "application/json" -Body $loginReq
$loginResp | ConvertTo-Json -Depth 6 | Write-Host

if ($loginResp.bound -eq $true) {
    $accessToken = $loginResp.access_token
    $refreshToken = $loginResp.refresh_token
} else {
    if (-not $loginResp.bind_ticket) {
        throw "No bind_ticket returned from wechat-login."
    }

    Write-Host "[2/6] MP customer bind..." -ForegroundColor Cyan
    $bindReq = @{
        bind_ticket = $loginResp.bind_ticket
        phone = $Phone
        plate_no = $PlateNo
        verify_code = "123456"
    } | ConvertTo-Json
    $bindResp = Invoke-RestMethod -Uri "$BaseUrl/mp/customer/auth/bind" -Method Post -ContentType "application/json" -Body $bindReq
    $bindResp | ConvertTo-Json -Depth 6 | Write-Host

    $accessToken = $bindResp.access_token
    $refreshToken = $bindResp.refresh_token
}

if (-not $accessToken) {
    throw "Access token is empty after login/bind."
}

$headers = @{ Authorization = "Bearer $accessToken" }

Write-Host "[3/6] MP customer me..." -ForegroundColor Cyan
$me = Invoke-RestMethod -Uri "$BaseUrl/mp/customer/me" -Method Get -Headers $headers
$me | ConvertTo-Json -Depth 6 | Write-Host

Write-Host "[4/6] MP customer vehicles..." -ForegroundColor Cyan
$vehicles = Invoke-RestMethod -Uri "$BaseUrl/mp/customer/vehicles" -Method Get -Headers $headers
$vehicles | ConvertTo-Json -Depth 6 | Write-Host
if ($vehicles.Count -lt 1) {
    throw "No vehicles returned for customer."
}
$vehicleId = $vehicles[0].id

Write-Host "[5/6] MP customer home..." -ForegroundColor Cyan
$home = Invoke-RestMethod -Uri "$BaseUrl/mp/customer/home?vehicle_id=$vehicleId" -Method Get -Headers $headers
$home | ConvertTo-Json -Depth 6 | Write-Host

if ($refreshToken) {
    Write-Host "[6/6] MP customer refresh..." -ForegroundColor Cyan
    $refreshReq = @{ refresh_token = $refreshToken } | ConvertTo-Json
    $refreshResp = Invoke-RestMethod -Uri "$BaseUrl/mp/customer/auth/refresh" -Method Post -ContentType "application/json" -Body $refreshReq
    $refreshResp | ConvertTo-Json -Depth 6 | Write-Host
    if (-not $refreshResp.access_token) {
        throw "Refresh endpoint did not return access_token."
    }
} else {
    Write-Host "[6/6] MP customer refresh skipped (no refresh token)" -ForegroundColor Yellow
}

Write-Host "MP customer preflight passed." -ForegroundColor Green
