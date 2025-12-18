# MCP Team 13 — Infra / SRE / Release Engineering

> Updated: 2025-12-17  
> Role: Own deployability, reliability, and release gates. This team turns the repo into a runnable, observable, recoverable system.

## Mission
Deliver production-grade operational readiness:
- one-command environment start
- CI gates (smoke + POCs)
- backup/restore rehearsal
- monitoring/alerting + structured logs + trace_id propagation
- secure secrets and environment management

## Inputs (must read)
- `docs/master_spec.md` (non-functional requirements, invariants)
- `docs/test_acceptance.md` (release gates)
- `infra/*`
- `scripts/*`
- `docs/security_baseline.md`
- `docs/capacity_plan.md`

## Outputs (deliverables)
1. `infra/docker-compose.yml` (MVP baseline)
   - Odoo + Postgres
   - Redis (if used by BFF)
   - Object storage (MinIO)
   - (Optional) MQ, Vector DB, TS DB (feature-flagged)
2. `infra/.env.example` updated to cover all components
3. Runbooks:
   - `infra/runbook.md` (start/stop/upgrade)
   - `infra/backup_restore.md` (how to back up + restore)
   - `infra/monitoring.md` (dashboards + alerts)
4. CI pipeline definition (location TBD by your CI system):
   - build
   - unit tests
   - `scripts/smoke_test.sh`
   - `scripts/poc_inventory.sh` (when endpoints exist)
   - `scripts/poc_payment.sh` (when endpoints exist)
   - `scripts/poc_ai_readonly.sh` (when AI exists)
5. Evidence artifacts:
   - a written backup/restore rehearsal record (date, steps, outcome)

## Non-negotiables (MUST)
1. Recoverability: tested backup and restore procedure (not theoretical).
2. Gates are real: a release is blocked unless smoke + required POCs pass.
3. Secrets: no secrets committed to repo. `.env.example` only.
4. Observability: logs are structured and include `trace_id` end-to-end.
5. Data safety: protect Postgres from accidental destructive operations.

## Definition of Done
- A new machine can start the full stack from README/runbook with minimal steps
- Backup/restore rehearsal has been executed at least once and documented
- CI reliably blocks regressions on core gates
