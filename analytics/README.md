# Analytics & Reporting

## Purpose
Metrics definitions, reporting pipelines, and dashboards. MVP can be lightweight exports; later can evolve into a warehouse/BI stack.

## Scope (MVP)
- metric_dictionary.md
- dashboards/ (optional)
- etl/ (optional)

## Interfaces
- Consumes immutable payment ledger + posted inventory moves via BFF/Odoo export.
- Never changes transactional truth.

## Local development (high level)
1. Define KPIs in metric_dictionary.md.
1. Add ETL jobs only after MVP is stable.

## Notes / Rules
- Do not bypass the BFF for client access.
- Keep secrets out of git; use environment variables.
- For transactional flows (inventory/payment), ensure idempotency and audit logs.
