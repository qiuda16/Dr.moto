# Architecture

> Date: 2025-12-17

## 1. High-level Components
- Odoo (ERP + inventory truth)
- BFF/API (single external entrypoint)
- Clients (WeChat mini-program, staff console, CS workspace)
- AI services (read-mostly, non-blocking)
- MQ (async events/tasks)
- Object Storage (media)
- Redis (cache/locks)
- Observability (logs/metrics/tracing)

## 2. Data Ownership
- Inventory and accounting postings: Odoo
- External API contract: BFF
- Immutable payment ledger: BFF (and/or Odoo accounting integration)

## 3. Critical Flows
### 3.1 Issue parts
Client -> BFF (idempotent) -> Odoo (post picking) -> BFF updates WO view -> emit event

### 3.2 Payment
Client -> BFF create order -> WeChat -> callback -> BFF verify+idempotent -> close WO -> emit event

## 4. Non-negotiables
- No direct DB access from clients
- No direct mutation of Odoo stock/accounting tables
- Idempotency on inventory/payment
- Auditability for privileged actions
