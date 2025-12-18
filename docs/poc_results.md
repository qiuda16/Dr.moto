# POC Results

> Date: 2025-12-17

## POC-1 Inventory Issue/Return Idempotency
### Goal
- Same idempotency key -> only one posted Odoo picking.

### Setup
- Odoo running
- One product with stock
- One work order in IN_PROGRESS

### Steps
1. Call issue endpoint twice with same Idempotency-Key
2. Verify Odoo picking count and state
3. Call return endpoint and verify net inventory

### Results
- Status: TBD
- Evidence: links/screenshots/logs: TBD
- Notes: TBD

## POC-2 WeChat Payment Callback Verification + Idempotency
### Goal
- Duplicate callbacks do not create duplicate payments and do not double-close work order.

### Results
- Status: TBD
- Evidence: TBD

## POC-3 AI CS Read-only Integration
### Goal
- AI can answer KB questions and query work order status via BFF read-only APIs.
- AI never writes transactional data directly.

### Results
- Status: TBD
- Evidence: TBD
