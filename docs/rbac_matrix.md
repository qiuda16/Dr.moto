# RBAC Matrix (MVP)

> Date: 2025-12-17  
> Principle: server-side enforcement (BFF/Odoo). UI gating is not sufficient.

## Roles
- OWNER (store owner / manager)
- ADVISOR (front desk)
- TECH (technician)
- KEEPER (warehouse keeper)
- CASHIER (cashier)
- ADMIN (system admin)
- CUSTOMER (wechat user)

## Data Scope
- Default: staff can only access `shop_id` they belong to.
- CUSTOMER can only access their own records (ownership by `customer_id`).

## Action Catalog (stable IDs)
Use these IDs in code (policy checks, audit logs, tests):

### Work Order
- `WO_CREATE`, `WO_VIEW`, `WO_UPDATE_BASIC`, `WO_STATUS_TRANSITION`, `WO_CANCEL`

### Quote / Pricing
- `QUOTE_CREATE_VERSION`, `QUOTE_EDIT_DRAFT`, `QUOTE_REQUEST_CONFIRM`, `QUOTE_OVERRIDE_AFTER_CONFIRM`, `DISCOUNT_APPLY`

### Inventory
- `INV_REQUEST_ISSUE`, `INV_POST_ISSUE`, `INV_POST_RETURN`, `INV_REVERSE`

### Payment
- `PAY_CREATE_ORDER`, `PAY_RECORD_OFFLINE`, `PAY_REFUND`, `WO_CLOSE`

### Admin / Master Data
- `USER_ROLE_MANAGE`

## Matrix
Legend: ✅ allowed, ❌ denied, 🔒 requires approval (OWNER/ADMIN), ℹ️ read-only

| Action | OWNER | ADVISOR | TECH | KEEPER | CASHIER | ADMIN | CUSTOMER |
|---|---|---|---|---|---|---|---|
| WO_CREATE | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ | ✅ |
| WO_VIEW | ✅ | ✅ | ✅ (assigned) | ✅ (inv-related) | ✅ | ✅ | ✅ (own) |
| WO_UPDATE_BASIC | ✅ | ✅ | ✅ (notes only) | ❌ | ❌ | ✅ | ❌ |
| WO_STATUS_TRANSITION | ✅ | ✅ | ✅ (IN_PROGRESS/READY) | ❌ | ❌ | ✅ | ❌ |
| WO_CANCEL | ✅ | 🔒 | ❌ | ❌ | ❌ | ✅ | ❌ |
| QUOTE_CREATE_VERSION | ✅ | ✅ | 🔒 (suggest only) | ❌ | ❌ | ✅ | ❌ |
| QUOTE_EDIT_DRAFT | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ |
| QUOTE_OVERRIDE_AFTER_CONFIRM | ✅ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ |
| INV_REQUEST_ISSUE | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ | ❌ |
| INV_POST_ISSUE | ✅ | ❌ | ❌ | ✅ | ❌ | ✅ | ❌ |
| INV_POST_RETURN | ✅ | ❌ | ❌ | ✅ | ❌ | ✅ | ❌ |
| INV_REVERSE | ✅ | ❌ | ❌ | 🔒 | ❌ | ✅ | ❌ |
| PAY_CREATE_ORDER | ✅ | ✅ | ❌ | ❌ | ✅ | ✅ | ✅ |
| PAY_RECORD_OFFLINE | ✅ | ✅ | ❌ | ❌ | ✅ | ✅ | ❌ |
| PAY_REFUND | ✅ | ❌ | ❌ | ❌ | 🔒 | ✅ | ❌ |
| WO_CLOSE | ✅ | ❌ | ❌ | ❌ | ✅ | ✅ | ❌ |
| USER_ROLE_MANAGE | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ |

## Enforcement Notes
- Any 🔒 action MUST create an `audit_log` entry including reason and before/after summary.
- TECH must not post inventory or payments.
