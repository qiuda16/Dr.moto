# Product Maturity Upgrade Plan (Big-Tech Standard)

Updated: 2026-03-29

## Goals

- Stable operations for daily store usage.
- Consistent API contracts for multi-client integration.
- Security and auditability by default.
- Clear roadmap from phase-1 MVP to phase-3 scale.

## Completed in this round

- Unified error response format with `trace_id`.
- Request-level tracing and latency headers (`X-Trace-Id`, `X-Process-Time-Ms`).
- Split health probes:
  - `GET /health/live`
  - `GET /health/ready`
- Added paginated query endpoints:
  - `GET /mp/workorders/search/page`
  - `GET /mp/inventory/products/page`
- Added idempotency support for payment intent creation (`Idempotency-Key`).

## Next high-priority backlog

1. API Standardization
- Add response envelope for all success responses (`success/data/meta`).
- Add versioned OpenAPI (`/v1/*`) and strict backward-compat policy.

2. Domain Consistency
- Work order lifecycle hard enforcement in BFF and Odoo.
- Quote versioning with publish/confirm states and immutable snapshots.
- Payment close-loop (intent -> callback -> ledger -> order closure).

3. Security
- Fine-grained role model split (`advisor`, `technician`) from current `staff`.
- Token revocation and session management.
- Secrets vault integration and rotation schedule.

4. Observability
- Structured logs in JSON.
- Metrics endpoint and dashboard (latency, error ratio, order throughput).
- Alert rules for degraded health and payment failures.

5. Reliability
- Replace runtime `create_all` with Alembic migrations.
- Add retry policy for Odoo RPC and outbound webhook calls.
- Circuit breaker on unstable dependencies.

6. Product UX
- Unified document theme with legal footer + store branding.
- Bulk operations and filter presets for front desk.
- Staff dashboard with SLA and queue views.
