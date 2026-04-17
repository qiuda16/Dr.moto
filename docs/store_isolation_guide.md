# Store Isolation Guide

Updated: 2026-03-29

## 1. Scope

BFF local-domain data now supports store scoping via `store_id`.

Scoped objects include:

- work orders
- quote versions
- payment ledger/events
- audit logs
- work order attachments

## 2. How store is resolved

Per request priority:

1. `X-Store-Id` request header
2. `store_id` query parameter
3. fallback to `BFF_DEFAULT_STORE_ID` (default: `default`)

## 3. Client integration

All staff/client requests should carry:

```http
X-Store-Id: <your_store_code>
```

Example:

```powershell
curl -H "Authorization: Bearer <token>" -H "X-Store-Id: store-a" http://localhost:8080/mp/workorders/list/page
```

## 4. Ops validation

Run smoke per store:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/smoke_test.ps1 -StoreId default
powershell -ExecutionPolicy Bypass -File scripts/smoke_test.ps1 -StoreId store-a
```

## 5. Notes

- UUID is globally unique, but query/read APIs are now store-scoped.
- For full enterprise multi-tenant isolation, Odoo-side partition strategy should be aligned with business org model.
