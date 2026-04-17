# Non-AI Module Test Report

Date: 2026-04-08
Executor: Codex

## Scope

- `web_staff` non-AI business modules
- `mp_customer`
- `mp_staff`
- `web_display`
- Representative BFF endpoints behind these modules

## Route Coverage

### `web_staff`

- Dashboard: `/`
- Work-order center: `/orders`
- Customer archive: `/customers`
- Inventory management: `/inventory`

### `mp_customer`

- Login / binding
- Dashboard
- Health archive
- Maintenance records
- Recommendations
- Knowledge
- Profile

### `mp_staff`

- Login
- Task board
- Workbench / work-order detail

### `web_display`

- Single public display board page

## Representative API Regression

### Dashboard and work orders

- `GET /mp/dashboard/overview`: passed
- `GET /mp/dashboard/summary`: passed
- `GET /mp/workorders/active/list`: passed with staff auth
- `GET /mp/workorders/list/page?page=1&size=10`: passed
- `GET /mp/workorders/{order_id}`: passed
- `GET /mp/workorders/{order_id}/timeline`: passed
- `GET /mp/workorders/{order_id}/actions`: passed

### Customers

- `GET /mp/workorders/customers/with-vehicles?limit=10`: passed
- `GET /mp/workorders/customers/{customer_id}/vehicles`: passed
- `GET /mp/workorders/customers/{customer_id}/orders`: passed
- `GET /mp/workorders/customers/{customer_id}/summary`: passed

### Inventory and knowledge

- `GET /mp/catalog/vehicle-models/brands`: passed
- `GET /mp/catalog/vehicle-models/categories`: passed
- `GET /mp/catalog/parts?page=1&size=10`: passed
- `GET /mp/catalog/vehicle-models/{model_id}/specs`: passed
- `GET /mp/catalog/vehicle-models/{model_id}/service-items`: passed
- `GET /mp/catalog/vehicle-models/{model_id}/service-packages`: passed
- `GET /mp/knowledge/documents`: passed
- `GET /mp/knowledge/catalog-models/{model_id}/procedures`: passed

### Customer mini-app

- `POST /mp/customer/auth/wechat-login`: passed
  - Verified bind-ticket flow is still returned correctly for an unbound code.

### Staff mini-app

- `GET /mp/workorders/active/list`: passed with staff auth
- `GET /mp/inventory/products?query=test`: passed
- `GET /mp/workorders/{order_id}`: passed

## Issues Found and Fixed

### `web_display` runtime authorization mismatch

- Problem:
  - The display screen called `GET /api/mp/workorders/active/list` without authentication.
  - That endpoint correctly required staff roles, so the display page would receive `401 Unauthorized` at runtime even though the frontend build succeeded.
- Fix:
  - Added a new public, read-only endpoint: `GET /mp/workorders/display/list`
  - Kept `GET /mp/workorders/active/list` protected for staff users
  - Updated `clients/web_display/src/App.vue` to use the new public endpoint

## Validation After Fix

- `GET /mp/workorders/display/list`: passed without auth
- `GET /mp/workorders/active/list`: still requires auth as expected
- `clients/web_display` production build: passed

## Remaining Risks

- This round focused on representative API and build verification, not full browser-driven click-through coverage.
- `web_staff` and `cs_workspace` still have bundle-size warnings during build.
- `mp_customer_uni` still reports Sass deprecation warnings during build.

## Conclusion

- Non-AI core modules are currently in a usable state for delivery.
- A real runtime issue was found in the public display board path and has now been fixed.
- No blocking crash, deadlock, or cross-module outage was reproduced in this test round.
