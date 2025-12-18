# MCP Team 2 — Work Order Domain

> Updated: 2025-12-17  
> Role: Work order lifecycle, diagnostics, quote versions, close rules.

## Mission
Deliver correct, auditable work order domain for MVP flow.

## Inputs
- `docs/master_spec.md`
- `docs/rbac_matrix.md`
- frozen OpenAPI
- `odoo/README.md`

## Outputs
- Odoo models/views/ACL (work_order, quote, status logs)
- BFF APIs for WO + quote (as specified)
- Server-side transition guards
- Acceptance tests for invariants

## MUST
- Every transition writes `wo_status_log` with operator/reason/trace_id
- Quote edits create new version; history preserved
- CLOSED invariants enforced

## Done
- state machine enforced server-side
- version history queryable
