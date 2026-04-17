# WeChat Mini-Program (Customer)

## Purpose
Customer-facing mini-program for vehicle management, creating service requests/work orders, viewing progress, confirming quotes, and paying.

## Current Skeleton (2026-03-30)
- App shell with guarded routes (`/login` + `/app/*`)
- Pinia stores for auth session and active vehicle
- API module split (`auth`, `vehicle`) with unified HTTP client
- Core pages scaffolded:
  - Dashboard
  - Health records
  - Maintenance orders
  - Recommended services
  - Knowledge docs
  - Profile center
- Ready for progressive detail filling without restructuring

## Interfaces
- Calls BFF REST endpoints only
- Uploads media via BFF presigned upload flow

## Non-negotiables
- All operations go through **BFF** (no direct DB/Odoo).
- Use `trace_id` in requests where supported.
- For payment and inventory-related flows, ensure idempotency is respected.

## Run / Build
```bash
npm install
npm run dev
```

Default local proxy:
- Frontend: `http://localhost:3000`
- BFF API target: `http://localhost:8080`
