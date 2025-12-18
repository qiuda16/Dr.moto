# Runbook

> Date: 2025-12-17

## 1. Local bring-up (minimum)
1. Start infrastructure (Odoo + Postgres + Redis + MQ + storage stub).
2. Confirm Odoo is reachable.
3. Install Odoo addons (drmoto_mro).
4. Start BFF and run smoke tests.

## 2. Backup
- Perform daily backups of Postgres.
- Verify backups by restoring to a fresh environment.

## 3. Restore Drill (minimum monthly)
1. Provision fresh Postgres volume
2. Restore backup
3. Start Odoo and validate login
4. Run smoke tests through BFF

## 4. Incident SOP (high-level)
- Payment callback errors: verify idempotency table, retry safely.
- Inventory posting errors: do not retry blindly; inspect Odoo move state; use idempotency keys.
