$ErrorActionPreference = "Stop"
$BFF_BASE = "http://localhost:8080"

Write-Host "[SMOKE] Checking BFF Health at $BFF_BASE/health ..." -ForegroundColor Cyan

try {
    $response = Invoke-RestMethod -Uri "$BFF_BASE/health" -Method Get
    Write-Host "[OK] BFF is Online:" -ForegroundColor Green
    Write-Host ($response | ConvertTo-Json)
} catch {
    Write-Host "[FAIL] Could not connect to BFF. Is Docker running?" -ForegroundColor Red
    Write-Host $_.Exception.Message
    exit 1
}

Write-Host "`n[SMOKE] Creating Test Work Order..." -ForegroundColor Cyan
try {
    $body = @{
        customer_id = "smoke_test"
        vehicle_plate = "TEST001"
        description = "Smoke Test Auto"
    } | ConvertTo-Json

    $wo = Invoke-RestMethod -Uri "$BFF_BASE/mp/workorders/create" -Method Post -Body $body -ContentType "application/json"
    Write-Host "[OK] Work Order Created:" -ForegroundColor Green
    Write-Host ($wo | ConvertTo-Json)
    
    $woId = $wo.id
    
    Write-Host "`n[SMOKE] Retrieving Work Order $woId..." -ForegroundColor Cyan
    $getWo = Invoke-RestMethod -Uri "$BFF_BASE/mp/workorders/$woId" -Method Get
    Write-Host "[OK] Work Order Retrieved" -ForegroundColor Green

    Write-Host "`n[SMOKE] Recording Payment for Work Order $woId..." -ForegroundColor Cyan
    $payBody = @{
        work_order_id = $woId
        amount = 100.00
        transaction_id = "txn_$(Get-Random)"
    } | ConvertTo-Json
    
    $pay = Invoke-RestMethod -Uri "$BFF_BASE/mp/payments/record" -Method Post -Body $payBody -ContentType "application/json"
    Write-Host "[OK] Payment Recorded:" -ForegroundColor Green
    Write-Host ($pay | ConvertTo-Json)

    Write-Host "`n[SMOKE] Uploading Media to Object Storage..." -ForegroundColor Cyan
    $content = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes("hello drmoto"))
    $uploadBody = @{
        filename = "smoke_$(Get-Random).txt"
        content_base64 = $content
        content_type = "text/plain"
    } | ConvertTo-Json
    $upload = Invoke-RestMethod -Uri "$BFF_BASE/media/upload_base64" -Method Post -Body $uploadBody -ContentType "application/json"
    Write-Host "[OK] Media Uploaded:" -ForegroundColor Green
    Write-Host ($upload | ConvertTo-Json)

} catch {
    Write-Host "[FAIL] Work Order flow failed" -ForegroundColor Red
    Write-Host $_.Exception.Message
    exit 1
}

Write-Host "`n[SMOKE] All Checks Passed" -ForegroundColor Green
