# Delivery Report (Backend Product Maturity)

Date: 2026-03-29

## Delivered Scope

- Stable Docker deployment for Odoo + BFF + DB + Redis + MinIO.
- Chinese input compatibility validated end-to-end (API + DB UTF-8 storage).
- Role-based access control expanded and hardened for critical endpoints.
- Work order core flow:
  - create customer
  - create work order
  - status transition with strict validation
  - upload attachments
  - render printable documents
- Quote lifecycle:
  - create version
  - publish
  - confirm
  - reject
  - list versions
- Observability and reliability:
  - request trace id propagation
  - structured error responses
  - metrics endpoint for request rate/latency/in-flight monitoring
  - liveness/readiness probes
  - idempotency for core write operations
  - login rate limiting
  - release gate script for consistent deployment validation
  - child-script exit-code enforcement in release/cutover/rollback orchestration (fail-fast pipeline behavior)

## Validation Evidence

- `pytest` in container: passing.
- `pytest` latest run: 14 passed.
- `scripts/preflight_prod.ps1`: passing.
- `scripts/smoke_test.ps1`: passing.
- `scripts/backup_stack.ps1`: successful backup snapshot generated.
- `scripts/alert_check.ps1`: passing.
- `scripts/failure_drill.ps1`: passing (degradation detected and readiness recovered).
- multi-store smoke (`scripts/smoke_test.ps1 -StoreId default/store-a`): passing.
- payment webhook flow (store-scoped) covered by automated test: passing.
- `scripts/release_gate.ps1 -SkipBackup`: passing (build + migration + preflight + smoke).
- `scripts/release_gate.ps1` negative test with mismatched `-ExpectedEnv`: fails as expected and blocks pipeline.
- `scripts/export_acceptance_pack.ps1`: passing, latest pack generated.
- `scripts/cutover_prod.ps1 -EnvFile infra/.env.prod.sample -ExpectedEnv prod -SkipBackup`: blocked as expected (`mock` payment provider warning in fail-on-warning mode).
- `scripts/cutover_prod.ps1 -EnvFile infra/.env.dev.sample -ExpectedEnv dev -SkipBackup`: passing.

Latest generated evidence folders:

- `infra/reports/alerts/alert_check_20260329_153958.json`
- `infra/reports/acceptance/20260329_154000/`
- `infra/reports/alerts/alert_check_20260329_154720.json`
- `infra/reports/acceptance/20260329_154723/`

## Operational Assets

- Go-live checklist.
- RBAC matrix.
- Document output guide.
- Backup and restore scripts.
- Release notes and maturity roadmap.
- One-command production cutover script (`scripts/cutover_prod.ps1`).
- Acceptance evidence export script (`scripts/export_acceptance_pack.ps1`).
- Production env validation script (`scripts/validate_prod_env.ps1`).

## Residual Risks / Deferred Items

- Payment gateway is still mock-mode unless real provider integration is added.
- SQL migration framework is in place; Alembic-based migration workflow is optional future enhancement.
- Multi-store strict data partitioning is now available for core local-domain objects via `store_id` scope (header/query driven); Odoo-side hard partition still requires business configuration alignment.
- Frontend UX still needs enterprise-level polishing (bulk actions, advanced filters, SLA dashboard).

## Delivery Decision

Current backend is acceptable for controlled production pilot in a single-store operation with standard security hardening applied in `.env`.
