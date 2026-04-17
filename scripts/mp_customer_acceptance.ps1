param(
    [string]$BaseUrl = "http://localhost:8080",
    [string]$Phone,
    [string]$PlateNo,
    [string]$StoreId = "default",
    [string]$MockCode = "acceptance-code-001",
    [string]$ReportPath = "infra/reports/mp_customer_acceptance.json"
)

$ErrorActionPreference = "Stop"

if (-not $Phone) { throw "Phone is required. Example: -Phone 13800138000" }
if (-not $PlateNo) { throw "PlateNo is required. Example: -PlateNo 沪A12345" }

$report = [ordered]@{
    started_at = (Get-Date).ToString("o")
    base_url = $BaseUrl
    checks = @()
}

function Add-CheckResult {
    param(
        [string]$Name,
        [bool]$Passed,
        [object]$Data = $null
    )
    $report.checks += [ordered]@{
        name = $Name
        passed = $Passed
        data = $Data
        at = (Get-Date).ToString("o")
    }
    if ($Passed) {
        Write-Host "[PASS] $Name" -ForegroundColor Green
    } else {
        Write-Host "[FAIL] $Name" -ForegroundColor Red
    }
}

try {
    $loginBody = @{ code = $MockCode; store_id = $StoreId } | ConvertTo-Json
    $loginResp = Invoke-RestMethod -Uri "$BaseUrl/mp/customer/auth/wechat-login" -Method Post -ContentType "application/json" -Body $loginBody
    Add-CheckResult -Name "wechat-login reachable" -Passed $true -Data $loginResp

    $accessToken = $null
    $refreshToken = $null
    if ($loginResp.bound -eq $true) {
        $accessToken = $loginResp.access_token
        $refreshToken = $loginResp.refresh_token
    } else {
        $bindBody = @{
            bind_ticket = $loginResp.bind_ticket
            phone = $Phone
            plate_no = $PlateNo
            verify_code = "123456"
        } | ConvertTo-Json
        $bindResp = Invoke-RestMethod -Uri "$BaseUrl/mp/customer/auth/bind" -Method Post -ContentType "application/json" -Body $bindBody
        Add-CheckResult -Name "bind success" -Passed ($bindResp.bound -eq $true) -Data $bindResp
        $accessToken = $bindResp.access_token
        $refreshToken = $bindResp.refresh_token
    }

    if (-not $accessToken) {
        throw "No access token obtained."
    }
    $headers = @{ Authorization = "Bearer $accessToken" }

    $me = Invoke-RestMethod -Uri "$BaseUrl/mp/customer/me" -Method Get -Headers $headers
    Add-CheckResult -Name "me endpoint" -Passed ($me.partner_id -gt 0) -Data $me

    $vehicles = Invoke-RestMethod -Uri "$BaseUrl/mp/customer/vehicles" -Method Get -Headers $headers
    $hasVehicle = ($vehicles -and $vehicles.Count -gt 0)
    Add-CheckResult -Name "vehicles endpoint" -Passed $hasVehicle -Data $vehicles
    if (-not $hasVehicle) {
        throw "No vehicle returned."
    }
    $vehicleId = $vehicles[0].id

    $home = Invoke-RestMethod -Uri "$BaseUrl/mp/customer/home?vehicle_id=$vehicleId" -Method Get -Headers $headers
    Add-CheckResult -Name "home summary endpoint" -Passed ($null -ne $home.pending_recommendations) -Data $home

    $health = Invoke-RestMethod -Uri "$BaseUrl/mp/customer/vehicles/$vehicleId/health-records?limit=10" -Method Get -Headers $headers
    Add-CheckResult -Name "health records endpoint" -Passed ($null -ne $health) -Data @{ count = $health.Count }

    $orders = Invoke-RestMethod -Uri "$BaseUrl/mp/customer/vehicles/$vehicleId/maintenance-orders?page=1&size=10" -Method Get -Headers $headers
    Add-CheckResult -Name "maintenance list endpoint" -Passed ($null -ne $orders.total) -Data $orders

    if ($orders.total -gt 0 -and $orders.items.Count -gt 0) {
        $orderId = $orders.items[0].id
        $detail = Invoke-RestMethod -Uri "$BaseUrl/mp/customer/maintenance-orders/$orderId" -Method Get -Headers $headers
        Add-CheckResult -Name "maintenance detail endpoint" -Passed ($detail.id -eq $orderId) -Data $detail
    } else {
        Add-CheckResult -Name "maintenance detail endpoint" -Passed $true -Data @{ skipped = "no orders found" }
    }

    $reco = Invoke-RestMethod -Uri "$BaseUrl/mp/customer/vehicles/$vehicleId/recommended-services" -Method Get -Headers $headers
    Add-CheckResult -Name "recommended services endpoint" -Passed ($null -ne $reco) -Data @{ count = $reco.Count }

    $docs = Invoke-RestMethod -Uri "$BaseUrl/mp/customer/vehicles/$vehicleId/knowledge-docs" -Method Get -Headers $headers
    Add-CheckResult -Name "knowledge docs endpoint" -Passed ($null -ne $docs) -Data @{ count = $docs.Count }

    $subPutBody = @{
        vehicle_id = $vehicleId
        notify_enabled = $true
        remind_before_days = 7
        remind_before_km = 500
        prefer_channel = "wechat_subscribe"
    } | ConvertTo-Json
    $subPut = Invoke-RestMethod -Uri "$BaseUrl/mp/customer/subscriptions" -Method Put -ContentType "application/json" -Headers $headers -Body $subPutBody
    Add-CheckResult -Name "subscription upsert endpoint" -Passed ($subPut.id -gt 0) -Data $subPut

    $subList = Invoke-RestMethod -Uri "$BaseUrl/mp/customer/subscriptions" -Method Get -Headers $headers
    Add-CheckResult -Name "subscription list endpoint" -Passed ($subList.Count -ge 1) -Data $subList

    if ($refreshToken) {
        $refreshBody = @{ refresh_token = $refreshToken } | ConvertTo-Json
        $refresh = Invoke-RestMethod -Uri "$BaseUrl/mp/customer/auth/refresh" -Method Post -ContentType "application/json" -Body $refreshBody
        Add-CheckResult -Name "refresh endpoint" -Passed ([string]::IsNullOrWhiteSpace($refresh.access_token) -eq $false) -Data $refresh
    } else {
        Add-CheckResult -Name "refresh endpoint" -Passed $true -Data @{ skipped = "no refresh token returned" }
    }

    Invoke-RestMethod -Uri "$BaseUrl/mp/customer/auth/logout" -Method Post -Headers $headers | Out-Null
    Add-CheckResult -Name "logout endpoint" -Passed $true
}
catch {
    Add-CheckResult -Name "acceptance run" -Passed $false -Data $_.Exception.Message
    throw
}
finally {
    $report.finished_at = (Get-Date).ToString("o")
    $reportFile = Resolve-Path -Path "." | ForEach-Object { Join-Path $_ $ReportPath }
    $reportDir = Split-Path $reportFile -Parent
    if (-not (Test-Path $reportDir)) {
        New-Item -Path $reportDir -ItemType Directory -Force | Out-Null
    }
    ($report | ConvertTo-Json -Depth 8) | Set-Content -Path $reportFile -Encoding UTF8
    Write-Host "Acceptance report saved: $reportFile" -ForegroundColor Cyan
}
