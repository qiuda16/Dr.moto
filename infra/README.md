# Infrastructure & DevOps

## Purpose
Docker Compose, environment configuration, secrets management, backups, observability bootstrap, and runbooks.

## Scope (MVP)
- docker-compose.yml (later)
- .env.example
- runbook.md
- backup_restore.md
- monitoring.md

## Interfaces
- Exposes local/dev endpoints via compose (e.g., Odoo:8069, BFF:8080).
- Provides scripts for DB backup/restore.

## Local development (high level)
1. Copy .env.example to .env and set secrets.
1. Run docker compose up -d from this folder (once compose is added).

## Notes / Rules
- Do not bypass the BFF for client access.
- Keep secrets out of git; use environment variables.
- For transactional flows (inventory/payment), ensure idempotency and audit logs.


## Related docs
- ../docs/runbook.md
- ../docs/capacity_plan.md
- ../docs/security_baseline.md
