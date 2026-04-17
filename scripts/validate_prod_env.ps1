param(
    [string]$EnvFile = "infra/.env",
    [string]$ExpectedEnv = "prod",
    [switch]$Strict,
    [switch]$FailOnWarnings
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $EnvFile)) {
    throw "Env file not found: $EnvFile"
}

$requiredKeys = @(
    "BFF_ENV",
    "BFF_SECRET_KEY",
    "BFF_WEBHOOK_SHARED_SECRET",
    "BFF_PAYMENT_PROVIDER",
    "BFF_PAYMENT_WEBHOOK_SECRET",
    "BFF_DB_AUTO_CREATE_TABLES",
    "BFF_AUTO_APPLY_MIGRATIONS",
    "BFF_STRICT_STARTUP_VALIDATION",
    "BFF_DEFAULT_STORE_ID"
)

$defaultRiskValues = @(
    "your-secret-key-change-me-in-production",
    "change_me_now",
    "replace_with_long_random_secret",
    "replace_with_strong_password",
    "replace_with_webhook_secret",
    "replace_with_payment_webhook_secret",
    "change_me"
)

$envMap = @{}
Get-Content $EnvFile | ForEach-Object {
    $line = $_.Trim()
    if (-not $line -or $line.StartsWith("#")) { return }
    $eq = $line.IndexOf("=")
    if ($eq -lt 1) { return }
    $key = $line.Substring(0, $eq).Trim()
    $val = $line.Substring($eq + 1).Trim()
    if ($val.StartsWith('"') -and $val.EndsWith('"') -and $val.Length -ge 2) {
        $val = $val.Substring(1, $val.Length - 2)
    }
    $envMap[$key] = $val
}

$errors = @()
$warnings = @()

foreach ($k in $requiredKeys) {
    if (-not $envMap.ContainsKey($k) -or [string]::IsNullOrWhiteSpace($envMap[$k])) {
        $errors += "Missing required key: $k"
    }
}

$hasPassword = $envMap.ContainsKey("BFF_ADMIN_PASSWORD") -and -not [string]::IsNullOrWhiteSpace($envMap["BFF_ADMIN_PASSWORD"])
$hasPasswordHash = $envMap.ContainsKey("BFF_ADMIN_PASSWORD_HASH") -and -not [string]::IsNullOrWhiteSpace($envMap["BFF_ADMIN_PASSWORD_HASH"])
if (-not $hasPassword -and -not $hasPasswordHash) {
    $errors += "Missing admin credential: provide BFF_ADMIN_PASSWORD or BFF_ADMIN_PASSWORD_HASH"
}

foreach ($pair in $envMap.GetEnumerator()) {
    $key = $pair.Key
    $val = $pair.Value
    if ($defaultRiskValues -contains $val) {
        $errors += "Risk default value detected: $key"
    }
}

if ($envMap.ContainsKey("BFF_ENV") -and $envMap["BFF_ENV"].ToLower() -ne $ExpectedEnv.ToLower()) {
    $warnings += "BFF_ENV is not $ExpectedEnv (current: $($envMap["BFF_ENV"]))"
}
if ($ExpectedEnv.ToLower() -eq "prod") {
    if ($envMap.ContainsKey("BFF_ENABLE_DEV_ENDPOINTS") -and $envMap["BFF_ENABLE_DEV_ENDPOINTS"].ToLower() -ne "false") {
        $warnings += "BFF_ENABLE_DEV_ENDPOINTS should be false"
    }
    if ($envMap.ContainsKey("BFF_ENABLE_MOCK_PAYMENT") -and $envMap["BFF_ENABLE_MOCK_PAYMENT"].ToLower() -ne "false") {
        $warnings += "BFF_ENABLE_MOCK_PAYMENT should be false in production"
    }
    if ($envMap.ContainsKey("BFF_DB_AUTO_CREATE_TABLES") -and $envMap["BFF_DB_AUTO_CREATE_TABLES"].ToLower() -ne "false") {
        $warnings += "BFF_DB_AUTO_CREATE_TABLES should be false in production"
    }
    if ($envMap.ContainsKey("BFF_AUTO_APPLY_MIGRATIONS") -and $envMap["BFF_AUTO_APPLY_MIGRATIONS"].ToLower() -ne "false") {
        $warnings += "BFF_AUTO_APPLY_MIGRATIONS should be false in production"
    }
}

if ($envMap.ContainsKey("BFF_PAYMENT_PROVIDER")) {
    $provider = $envMap["BFF_PAYMENT_PROVIDER"].ToLower()
    if ($provider -eq "wechat") {
        $wechatRequired = @(
            "BFF_WECHAT_MCH_ID",
            "BFF_WECHAT_APP_ID",
            "BFF_WECHAT_API_V3_KEY",
            "BFF_WECHAT_CERT_SERIAL_NO",
            "BFF_WECHAT_NOTIFY_URL"
        )
        foreach ($k in $wechatRequired) {
            if (-not $envMap.ContainsKey($k) -or [string]::IsNullOrWhiteSpace($envMap[$k])) {
                $errors += "Missing WeChat payment key: $k"
            }
        }
        $hasWechatKeyPem = $envMap.ContainsKey("BFF_WECHAT_MCH_PRIVATE_KEY_PEM") -and -not [string]::IsNullOrWhiteSpace($envMap["BFF_WECHAT_MCH_PRIVATE_KEY_PEM"])
        $hasWechatKeyPath = $envMap.ContainsKey("BFF_WECHAT_MCH_PRIVATE_KEY_PATH") -and -not [string]::IsNullOrWhiteSpace($envMap["BFF_WECHAT_MCH_PRIVATE_KEY_PATH"])
        if (-not $hasWechatKeyPem -and -not $hasWechatKeyPath) {
            $errors += "Missing WeChat private key: provide BFF_WECHAT_MCH_PRIVATE_KEY_PEM or BFF_WECHAT_MCH_PRIVATE_KEY_PATH"
        }
    } elseif ($provider -eq "mock") {
        if ($ExpectedEnv.ToLower() -eq "prod") {
            $warnings += "BFF_PAYMENT_PROVIDER=mock is for non-production testing only"
        }
    }
}

Write-Host "Env validation summary for: $EnvFile" -ForegroundColor Cyan
Write-Host ("Errors: {0}, Warnings: {1}" -f $errors.Count, $warnings.Count)

if ($warnings.Count -gt 0) {
    Write-Host "Warnings:" -ForegroundColor Yellow
    $warnings | ForEach-Object { Write-Host ("- " + $_) -ForegroundColor Yellow }
}

if ($errors.Count -gt 0) {
    Write-Host "Errors:" -ForegroundColor Red
    $errors | ForEach-Object { Write-Host ("- " + $_) -ForegroundColor Red }
    if ($Strict) {
        throw "Production env validation failed."
    }
}

if ($FailOnWarnings -and $warnings.Count -gt 0) {
    throw "Production env validation failed due to warnings."
}

Write-Host "Env validation completed." -ForegroundColor Green
