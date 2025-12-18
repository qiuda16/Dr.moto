# MCP Team 0 — Governance & Contracts

> Updated: 2025-12-17  
> Role: Contract authority for docs, contracts, acceptance criteria, and change control.

## Mission
Control shared language:
- master spec (business + non-functional)
- OpenAPI contracts and error codes
- RBAC action dictionary and approval points
- acceptance tests and release gates
- ADR decisions

## Inputs (must read)
- `docs/master_spec.md`
- `docs/prd_mvp.md`
- `docs/rbac_matrix.md`
- `docs/test_acceptance.md`
- `docs/adr/*`

## Outputs
- Frozen versions (tagged):
  - OpenAPI contract
  - error code dictionary
  - idempotency key spec
  - RBAC action catalog
  - acceptance gate checklist
- Change announcements
- ADR updates with consequences

## Operating rules (MUST)
1. No implementation starts without a defined contract.
2. Contract changes require: diff + migration notes + test updates.
3. Minimal but complete—no ambiguity on high-risk flows.

## Work template
1) Endpoint + method + auth + RBAC action_id
2) Request/response schema + error cases
3) Idempotency requirement (writes)
4) Audit requirement (privileged)
5) Acceptance tests

## Acceptance
- Another agent can implement without guessing.
