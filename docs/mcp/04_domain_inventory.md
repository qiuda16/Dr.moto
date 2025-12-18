# MCP Team 3 — Inventory Domain (POC-1)

> Updated: 2025-12-17  
> Role: Issue/return/reverse via Odoo stock postings; strict idempotency.

## Inputs
- `docs/master_spec.md`
- frozen OpenAPI for issue/return
- `scripts/poc_inventory.sh`

## Outputs
- Odoo picking/move posting logic
- BFF issue/return endpoints (Idempotency-Key)
- part line reconciliation (plan/issued/returned)
- audit logs for reverse/privileged actions

## MUST
- Only posted Odoo stock moves change inventory
- issue/return idempotent (unique key -> unique posting)
- no delete/overwrite; correct via reverse/return

## POC Gate
- `poc_inventory.sh` passes

## Done
- linkage: work_order_id <-> picking_id/move_id
