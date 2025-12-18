# Client Applications

## Purpose
All end-user applications. Split by audience: customer mini-program, staff console, and customer service workspace.

## Scope (MVP)
- mp_customer (WeChat mini-program)
- web_staff (staff console)
- cs_workspace (customer service)

## Interfaces
- All clients call BFF only (no direct DB/Odoo access).

## Local development (high level)
1. Each client has its own README with build/run steps.

## Notes / Rules
- Do not bypass the BFF for client access.
- Keep secrets out of git; use environment variables.
- For transactional flows (inventory/payment), ensure idempotency and audit logs.
