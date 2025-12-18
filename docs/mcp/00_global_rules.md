# MCP Prompt Pack — Global Rules (v1)

> Updated: 2025-12-17  
> Purpose: Global rules shared by all AI/MCP teams.  
> Priority: If any per-team rule conflicts with this file, this file wins.

## 0. Non-negotiables (MUST)
1. **Single Source of Truth**: `docs/master_spec.md` is the authority for business rules, boundaries, and non-functional constraints.
2. **Contract-first**: No implementation begins without a contract:
   - API: OpenAPI in `docs/api_contract.md` (or generated OpenAPI file under `docs/api/`).
   - Data: entities/fields in `docs/data_model.md` (and Odoo models accordingly).
3. **No bypassing the Gateway**: All clients/edge/AI write operations MUST go through the GW/BFF (`bff/`). No direct DB access from clients.
4. **Inventory truth in Odoo**: Inventory quantity changes MUST be posted via Odoo stock transactions only.
5. **Payment immutability**: Payment records are append-only / immutable. Corrections are via refund/chargeback records.
6. **Idempotency**: Any high-risk write endpoint MUST enforce Idempotency-Key with a unique constraint and replay-safe behavior.
7. **Auditability**: High-risk actions (price override, cancel, refund, reverse, manual close) MUST emit audit logs with reason.
8. **Closed means closed**: After `CLOSED`, you cannot mutate the financial/inventory facts; only create reversing/correcting artifacts.
9. **Media outside DB**: Store media in object storage (OBJ). DB stores metadata and URL only.
10. **Trace everywhere**: `trace_id` MUST be present in logs and propagated across calls.

## 1. Change control (MUST)
- Any change to:
  - status machine,
  - idempotency semantics,
  - inventory/payment flows,
  - or API contracts
  MUST be recorded in an ADR under `docs/adr/` and announced to all teams.

## 2. Definition of Done (baseline)
A task is DONE only if:
- Contract updated (OpenAPI / data model) where relevant
- Tests written/updated (unit + integration)
- Smoke/POC scripts remain passing or are updated with new expected behavior
- Audit & trace requirements satisfied for high-risk actions
- Docs updated (README or relevant doc)

## 3. Integration etiquette (MUST)
- Do not create hidden coupling. All cross-team dependencies must be explicit via:
  - OpenAPI
  - Events schema
  - Shared domain vocabulary in `master_spec.md`
