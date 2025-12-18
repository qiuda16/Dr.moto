# WeChat Mini-Program (Customer)

## Purpose
Customer-facing mini-program for vehicle management, creating service requests/work orders, viewing progress, confirming quotes, and paying.

## MVP features
- WeChat login -> BFF token
- Vehicle CRUD
- Create work order (text + media)
- Work order list/detail
- Quote confirmation
- WeChat pay initiate + status view

## Interfaces
- Calls BFF REST endpoints only
- Uploads media via BFF presigned upload flow

## Non-negotiables
- All operations go through **BFF** (no direct DB/Odoo).
- Use `trace_id` in requests where supported.
- For payment and inventory-related flows, ensure idempotency is respected.

## Run / Build
TBD (choose framework/tooling; keep it simple for MVP).
