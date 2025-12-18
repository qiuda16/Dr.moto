# MCP Team 1 — GW/BFF Platform

> Updated: 2025-12-17  
> Role: Gateway platform capabilities (auth, RBAC, idempotency, audit, trace). Not business logic.

## Mission
Provide a stable API platform for all domains and clients.

## Inputs
- `docs/master_spec.md`
- `docs/rbac_matrix.md`
- `docs/api_contract.md`
- `docs/test_acceptance.md`
- `docs/mcp/00_global_rules.md`

## Outputs
- BFF skeleton + `/health`
- Middlewares: auth, RBAC(action_id), idempotency, audit, trace_id
- Standard response envelope + error format
- Structured logging + observability hooks
- Adapters: Odoo/OBJ/MQ (stubs ok)

## Rules (MUST)
1. Platform stays generic; no domain rules embedded.
2. Idempotency enforced where contract requires.
3. RBAC enforced server-side.
4. Audit reason enforced on privileged actions.

## Done
- smoke tests pass
- middleware deterministic + documented
