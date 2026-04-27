# Scripts

Updated: 2026-03-29

Before production cutover, copy `infra/.env.prod.sample` to `infra/.env` and replace secrets.
For non-production dry-runs, use `infra/.env.dev.sample`.

## Day-1 Operations (PowerShell)

Note: if your local PowerShell profile has startup errors, run commands with `-NoProfile`, e.g.
`powershell -NoProfile -ExecutionPolicy Bypass -File scripts/pre_release_audit.ps1`.

- `scripts/preflight_prod.ps1`
  - checks container state, BFF health/readiness, optional runtime env match, Odoo module install status, and auth token flow.
- `scripts/preflight_mp_customer.ps1`
  - validates MP customer backend chain: wechat-login/bind, `/mp/customer/me`, `/vehicles`, `/home`, and refresh flow.
- `scripts/mp_customer_acceptance.ps1`
  - full MP customer API acceptance flow and writes JSON report to `infra/reports/mp_customer_acceptance.json`.
- `scripts/smoke_test.ps1`
  - end-to-end API smoke: login, create customer, create work order, render document (supports `-StoreId`).
- `scripts/backup_stack.ps1`
  - dumps PostgreSQL (`bff`, `odoo`) and copies MinIO data into timestamped backup directory.
- `scripts/restore_stack.ps1`
  - restores databases and MinIO data from a selected backup directory.
- `scripts/db_migrate.ps1`
  - applies versioned SQL migrations in `bff/migrations/versions` into BFF database.
- `scripts/release_gate.ps1`
  - one-command release gate: build, backup, migrate, preflight, smoke test (supports `-StoreId`, `-ExpectedEnv`, `-CheckReady`).
- `scripts/release_ready.ps1`
  - unified one-command entrypoint. Default runs full pre-release audit; optional `-RunReleaseGate` and `-RunProdCutover` chain into release/deployment workflow.
  - optional `-RunAiEnterpriseBrutal` adds AI enterprise brutal gate (quality + loop + brutal + chaos + memory/long-conversation checks) before release.
- `scripts/pre_release_audit.ps1`
  - lightweight pre-release audit for daily development: git cleanliness, backend pytest, staff frontend build, DB integrity audit, UTF-8 encoding audit, Chinese path smoke, and secret scan.
- `scripts/ocr_manual_brutal_test.py`
  - end-to-end OCR manual brutal test for upload -> parse -> catalog bind/confirm -> spec import -> segment materialization (with no-TOC soft fallback) -> service-item sync; outputs reports to `docs/recovery_reports`.
- `scripts/encoding_audit.py`
  - scans git-tracked source files for UTF-8 decode errors, replacement-char markers, and suspicious consecutive question marks; report is written to `infra/reports/encoding_audit`.
- `scripts/chinese_path_smoke.py`
  - verifies Chinese directory/file-name read-write roundtrip on current runtime and writes output under `infra/reports/runtime_smoke`.
- `scripts/secret_scan.py`
  - scans tracked source files for potential secret leaks (API keys/private key blocks), report written to `infra/reports/secret_scan`.
- `scripts/validate_prod_env.ps1`
  - validates `infra/.env` required keys, risky defaults, and payment provider config before production release.
- `scripts/alert_check.ps1`
  - evaluates live alert thresholds from `/health` + `/metrics` (5xx ratio, p95 latency, in-flight) and saves JSON report under `infra/reports/alerts`.
- `scripts/failure_drill.ps1`
  - performs controlled Odoo outage and measures readiness recovery time.
- `scripts/rollback_release.ps1`
  - restores from backup, reapplies migrations, and validates with preflight + smoke (supports `-StoreId`).
- `scripts/export_acceptance_pack.ps1`
  - exports deployment evidence (health/ready/metrics/migration/container status) to `infra/reports/acceptance/<timestamp>`.
- `scripts/cutover_prod.ps1`
  - one-command production cutover: env validation (strict + warnings fail) + release gate + alert check + acceptance pack export.

## Existing Validation/POC Scripts

- `smoke_test.sh`, `smoke_test_p1.py`, `smoke_test_p3.py`, `smoke_test_payment.py`
- `poc_inventory.sh`, `poc_payment.sh`, `poc_ai_readonly.sh`

## MySQL Cloud->Local Scheduled Sync (Low Cost Alternative to DTS)

- `scripts/mysql_sync_cloud_to_local.ps1`
  - low-cost sync from cloud MySQL to local MySQL.
  - `-Mode incremental`: sync rows changed since last watermark (`updated_at`/`created_at`/`create_date` tables).
  - `-Mode full`: full dump+import for baseline reconciliation.
- `scripts/setup_mysql_sync_tasks.ps1`
  - creates Windows Task Scheduler jobs:
    - every 15 minutes incremental sync
    - daily 03:00 full sync

Example manual run (incremental):

```powershell
powershell -ExecutionPolicy Bypass -File scripts/mysql_sync_cloud_to_local.ps1 `
  -SourceHost "10.22.107.252" -SourcePort 3306 -SourceUser "bff_user" -SourcePassword "<cloud_pwd>" -SourceDatabase "flask_demo" `
  -TargetHost "127.0.0.1" -TargetPort 3306 -TargetUser "root" -TargetPassword "<local_pwd>" -TargetDatabase "flask_demo" `
  -Mode incremental
```

Example manual run (full):

```powershell
powershell -ExecutionPolicy Bypass -File scripts/mysql_sync_cloud_to_local.ps1 `
  -SourceHost "10.22.107.252" -SourcePort 3306 -SourceUser "bff_user" -SourcePassword "<cloud_pwd>" -SourceDatabase "flask_demo" `
  -TargetHost "127.0.0.1" -TargetPort 3306 -TargetUser "root" -TargetPassword "<local_pwd>" -TargetDatabase "flask_demo" `
  -Mode full
```

Create scheduled tasks:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup_mysql_sync_tasks.ps1 `
  -SyncScriptPath "scripts/mysql_sync_cloud_to_local.ps1" `
  -IncrementalArgs "-SourceHost 10.22.107.252 -SourcePort 3306 -SourceUser bff_user -SourcePassword <cloud_pwd> -SourceDatabase flask_demo -TargetHost 127.0.0.1 -TargetPort 3306 -TargetUser root -TargetPassword <local_pwd> -TargetDatabase flask_demo -Mode incremental" `
  -FullArgs "-SourceHost 10.22.107.252 -SourcePort 3306 -SourceUser bff_user -SourcePassword <cloud_pwd> -SourceDatabase flask_demo -TargetHost 127.0.0.1 -TargetPort 3306 -TargetUser root -TargetPassword <local_pwd> -TargetDatabase flask_demo -Mode full"
```

## Demo Data Utilities

- `scripts/seed_demo_dataset_clean.py`
  - seeds a small clean demo dataset for AI/customer/work-order walkthroughs without the legacy mojibake issues.
- `scripts/repair_demo_text.ps1`
  - repairs the current demo text fields in Odoo + BFF databases for the main showcase records.

## Example Usage

```powershell
powershell -ExecutionPolicy Bypass -File scripts/preflight_prod.ps1
powershell -ExecutionPolicy Bypass -File scripts/preflight_prod.ps1 -ExpectedEnv "prod" -CheckReady
powershell -ExecutionPolicy Bypass -File scripts/preflight_mp_customer.ps1 -Phone "13800138000" -PlateNo "沪A12345"
powershell -ExecutionPolicy Bypass -File scripts/mp_customer_acceptance.ps1 -Phone "13800138000" -PlateNo "沪A12345"
powershell -ExecutionPolicy Bypass -File scripts/smoke_test.ps1
powershell -ExecutionPolicy Bypass -File scripts/db_migrate.ps1
powershell -ExecutionPolicy Bypass -File scripts/validate_prod_env.ps1 -EnvFile "infra/.env" -Strict
powershell -ExecutionPolicy Bypass -File scripts/release_gate.ps1 -AdminPassword "<your_admin_password>" -StoreId "default" -ExpectedEnv "prod" -CheckReady
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/release_ready.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/release_ready.ps1 -RunAiEnterpriseBrutal -AiAdminPassword "<your_admin_password>"
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/release_ready.ps1 -RunReleaseGate -AdminPassword "<your_admin_password>" -StoreId "default" -ExpectedEnv "prod" -CheckReady
python scripts/ocr_manual_brutal_test.py --quick-rounds 8 --quick-workers 4 --real-pdf 1_real_sample_12p.pdf --real-rounds 2 --real-workers 1 --cleanup-source-document
powershell -ExecutionPolicy Bypass -File scripts/pre_release_audit.ps1
python scripts/chinese_path_smoke.py
python scripts/secret_scan.py
powershell -ExecutionPolicy Bypass -File scripts/alert_check.ps1
powershell -ExecutionPolicy Bypass -File scripts/failure_drill.ps1 -FailureDurationSeconds 15
powershell -ExecutionPolicy Bypass -File scripts/rollback_release.ps1 -BackupDir "infra/backups/20260329_140000" -AdminPassword "<your_admin_password>" -StoreId "default"
powershell -ExecutionPolicy Bypass -File scripts/export_acceptance_pack.ps1
powershell -ExecutionPolicy Bypass -File scripts/cutover_prod.ps1 -EnvFile "infra/.env" -AdminPassword "<your_admin_password>" -StoreId "default"
powershell -ExecutionPolicy Bypass -File scripts/backup_stack.ps1
powershell -ExecutionPolicy Bypass -File scripts/restore_stack.ps1 -BackupDir "infra/backups/20260329_140000"
py -3.9 scripts/seed_demo_dataset_clean.py
powershell -ExecutionPolicy Bypass -File scripts/repair_demo_text.ps1
```
