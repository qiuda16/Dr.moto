# Resilience Drill Playbook

Updated: 2026-03-29

## 1. Purpose

Provide a repeatable failure-and-recovery drill for store operation continuity.

## 2. Prerequisites

- All services healthy (`/health` returns `ok`).
- Latest backup available under `infra/backups/`.
- Maintenance window approved for outage simulation.

## 3. Runbook

1. Baseline alert check:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/alert_check.ps1
```

2. Execute outage simulation:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/failure_drill.ps1 -FailureDurationSeconds 20
```

3. Validate business path:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/smoke_test.ps1
```

4. If validation fails, run rollback:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/rollback_release.ps1 -BackupDir "infra/backups/YYYYMMDD_HHMMSS" -AdminPassword "<your_admin_password>"
```

## 4. Drill Acceptance

- Readiness recovers within target SLA (for example <= 180s).
- Smoke test succeeds after recovery.
- Alert thresholds return to normal.
