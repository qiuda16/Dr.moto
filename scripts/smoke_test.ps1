param(
    [string]$BaseUrl = "http://localhost:18080",
    [string]$Username = "admin",
    [string]$Password = "change_me_now",
    [string]$StoreId = "default"
)

$ErrorActionPreference = "Stop"

Write-Host "[1/5] Health check..." -ForegroundColor Cyan
$health = Invoke-RestMethod -Uri "$BaseUrl/health" -Method Get
$health | ConvertTo-Json -Depth 6 | Write-Host
if ($health.status -ne "ok") {
    throw "Health is not ok."
}

Write-Host "[2/5] Login..." -ForegroundColor Cyan
$tokenResp = Invoke-RestMethod -Uri "$BaseUrl/auth/token" -Method Post -ContentType "application/x-www-form-urlencoded" -Body "username=$Username&password=$Password"
$token = $tokenResp.access_token
if (-not $token) { throw "Login failed." }
$headers = @{
    Authorization = "Bearer $token"
    "X-Store-Id" = $StoreId
}

Write-Host "[3/5] Create customer..." -ForegroundColor Cyan
$customer = Invoke-RestMethod -Uri "$BaseUrl/mp/workorders/customers" -Method Post -Headers $headers -ContentType "application/json" -Body (@{
    name = "Smoke Customer"
    phone = "13900000000"
    email = "smoke@example.com"
} | ConvertTo-Json)

Write-Host "[4/5] Create work order..." -ForegroundColor Cyan
$wo = Invoke-RestMethod -Uri "$BaseUrl/mp/workorders/" -Method Post -Headers $headers -ContentType "application/json" -Body (@{
    customer_id = "$($customer.id)"
    vehicle_plate = "SMOKE001"
    description = "Smoke test order"
} | ConvertTo-Json)

Write-Host "[5/5] Render document..." -ForegroundColor Cyan
$docResp = Invoke-WebRequest -Uri "$BaseUrl/mp/workorders/$($wo.id)/documents/work-order" -Method Get -Headers $headers
if ($docResp.StatusCode -ne 200) {
    throw "Document endpoint failed."
}

$actionsResp = Invoke-RestMethod -Uri "$BaseUrl/mp/workorders/$($wo.id)/actions" -Method Get -Headers $headers
if (-not $actionsResp.actions) {
    throw "Action endpoint failed."
}

$quote = Invoke-RestMethod -Uri "$BaseUrl/mp/quotes/$($wo.id)/versions" -Method Post -Headers $headers -ContentType "application/json" -Body (@{
    items = @(
        @{ item_type = "part"; code = "P-001"; name = "Brake Pad"; qty = 2; unit_price = 120 },
        @{ item_type = "service"; code = "L-001"; name = "Labor"; qty = 1; unit_price = 180 }
    )
} | ConvertTo-Json -Depth 6)
if ($quote.version -ne 1) {
    throw "Quote create failed."
}

$published = Invoke-RestMethod -Uri "$BaseUrl/mp/quotes/$($wo.id)/1/publish" -Method Post -Headers $headers
if ($published.status -ne "published") {
    throw "Quote publish failed."
}

$listPageUrl = "{0}/mp/workorders/list/page?page=1&size=10" -f $BaseUrl
$listPage = Invoke-RestMethod -Uri $listPageUrl -Method Get -Headers $headers
if (-not $listPage.items) {
    throw "Work order page endpoint failed."
}

$summary = Invoke-RestMethod -Uri "$BaseUrl/mp/dashboard/summary" -Method Get -Headers $headers
if (-not $summary.orders) {
    throw "Dashboard summary endpoint failed."
}

Write-Host "Smoke test passed." -ForegroundColor Green
Write-Host ("Work order id: " + $wo.id)
