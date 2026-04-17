# RBAC Matrix (Operational Baseline)

Updated: 2026-03-29

This matrix is the backend enforcement contract for the current BFF + Odoo deployment.

## Roles

- `admin`: platform administrator, full access.
- `manager`: store manager.
- `staff`: front desk / advisor / technician mixed role (phase-1 simplification).
- `keeper`: inventory and warehouse operator.
- `cashier`: payment and closing operator.

## Data Scope Rules

- All staff roles are store-internal only.
- Future customer-facing access must be isolated by customer ownership (`customer_id`) and should not reuse staff tokens.

## Endpoint Policy

| Area | Endpoint | Allowed Roles |
|---|---|---|
| Auth | `POST /auth/token` | Public |
| Work order | `POST /mp/workorders/` | `admin`, `manager`, `staff` |
| Work order | `GET /mp/workorders/{id}` | `admin`, `manager`, `staff`, `cashier`, `keeper` |
| Work order | `GET /mp/workorders/search` | `admin`, `manager`, `staff`, `cashier`, `keeper` |
| Work order | `POST /mp/workorders/{id}/status` | `admin`, `manager`, `staff` |
| Work order | `POST /mp/workorders/customers` | `admin`, `manager`, `staff` |
| Work order | `GET /mp/workorders/customers/search` | `admin`, `manager`, `staff` |
| Work order | `GET /mp/workorders/customers/{partner_id}/vehicles` | `admin`, `manager`, `staff` |
| Work order | `GET /mp/workorders/customers/{partner_id}/orders` | `admin`, `manager`, `staff` |
| Work order | `GET /mp/workorders/{id}/documents/{doc_type}` | `admin`, `manager`, `staff`, `cashier`, `keeper` |
| Inventory | `POST /mp/inventory/issue` | `admin`, `manager`, `keeper` |
| Inventory | `GET /mp/inventory/products` | `admin`, `manager`, `keeper`, `staff` |
| Payments | `POST /mp/payments/create_intent` | `admin`, `manager`, `cashier`, `staff` |
| Payments | `POST /mp/payments/record` | `admin`, `manager`, `cashier` |
| Events | `/mp/events/*` | `admin`, `manager` |
| Ops | `/media/*`, `/ops/*` | restricted admin/manager only |

## Notes

- `staff` is intentionally broad for phase-1 go-live. Split into dedicated advisor/technician roles in phase-2.
- Any override or cancellation action should always emit audit logs.
- No endpoint should rely on frontend visibility for security; always enforce role checks in backend dependencies.
