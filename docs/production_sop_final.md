# Production SOP Final

Updated: 2026-03-29

## 1. Daily Startup Check

```powershell
powershell -ExecutionPolicy Bypass -File scripts/preflight_prod.ps1 -AdminPassword "<admin_password>"
powershell -ExecutionPolicy Bypass -File scripts/alert_check.ps1
```

Expected:

- `/health` is `ok`
- alert report generated under `infra/reports/alerts/`

## 2. Release Procedure

```powershell
powershell -ExecutionPolicy Bypass -File scripts/release_gate.ps1 -AdminPassword "<admin_password>" -StoreId "default" -ExpectedEnv "prod" -CheckReady
```

Pipeline includes:

- build and start
- backup
- migration
- preflight
- smoke test

Recommended one-command production cutover:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/cutover_prod.ps1 -EnvFile "infra/.env" -AdminPassword "<admin_password>" -StoreId "default"
```

This workflow runs:

- strict env validation
- release gate
- alert threshold check
- acceptance evidence export (`infra/reports/acceptance/<timestamp>`)

Tip:

- Use `infra/.env.prod.sample` as a starting point for your production env file, then replace all secrets before go-live.
- `scripts/cutover_prod.ps1` defaults to `ExpectedEnv=prod` and fails on warnings; if `BFF_PAYMENT_PROVIDER=mock`, cutover will be blocked.

## 3. Failure Drill (Maintenance Window)

```powershell
powershell -ExecutionPolicy Bypass -File scripts/failure_drill.ps1 -FailureDurationSeconds 20
```

Then:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/smoke_test.ps1 -StoreId "default"
```

## 4. Rollback Procedure

```powershell
powershell -ExecutionPolicy Bypass -File scripts/rollback_release.ps1 -BackupDir "infra/backups/YYYYMMDD_HHMMSS" -AdminPassword "<admin_password>" -StoreId "default"
```

## 5. Payment Operation Notes

- Provider switch: `BFF_PAYMENT_PROVIDER=mock|wechat`
- WeChat callback:
  - URL: `/mp/payments/webhook/wechat`
  - Prefer WeChat platform certificate signature headers (`Wechatpay-*`)
  - Fallback shared secret: `X-Payment-Signature` + `BFF_PAYMENT_WEBHOOK_SECRET`

## 6. Weekly Archive

Archive:

- latest release logs
- alert JSON reports
- drill run timestamps and recovery duration
- latest acceptance pack folder (`infra/reports/acceptance/<timestamp>`)
