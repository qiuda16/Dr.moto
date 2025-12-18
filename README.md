# DrMoto Project (Monorepo)

This repository is organized as a set of **sub-projects** that can be developed and delivered independently while integrating through the **BFF/API** layer.

## Sub-projects
- `infra/` — infrastructure and DevOps
- `odoo/` — Odoo core configuration and custom addons
- `bff/` — external API gateway/BFF service (single entrypoint)
- `clients/` — WeChat mini-program and internal web apps
- `ai/` — AI customer service and future AI modules
- `analytics/` — reporting and KPI definitions
- `docs/` — architecture and specifications
- `scripts/` — setup and maintenance scripts

## Key non-negotiables (MUST)
1. **Inventory truth lives in Odoo** (all stock changes via Odoo posted transactions).
2. **Clients call BFF only** (no direct DB/Odoo access).
3. **Idempotency for critical actions** (issue/return/reverse/payment notify).
4. **Auditability** (status logs, audit logs, immutable payment records).

## Quick start (local)
1. Start with `infra/` (compose, env, Odoo+Postgres) and ensure Odoo is reachable.
2. Install `odoo/addons/drmoto_mro` to validate the addon mount path.
3. Bring up `bff/` and expose minimal APIs to the WeChat mini-program.

> Generated folder scaffold on 2025-12-17.
