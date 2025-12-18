# BFF / API Service

## Purpose
Single external entrypoint for all clients (WeChat mini-program, staff console, customer service). Implements auth, RBAC, idempotency, business orchestration, and integrations.

## Scope (MVP)
- app/ (FastAPI recommended)
- tests/
- openapi.yaml (generated)
- Dockerfile (later)

## Interfaces
- REST APIs to clients.
- Calls Odoo for inventory/ERP actions.
- Calls WeChat for login/payment/notifications.
- Publishes events to MQ.

## Local development (high level)
1. Install dependencies (poetry/pip) and run uvicorn.
1. Configure Odoo endpoint, Redis, MQ, object storage in env.

## Notes / Rules
- Do not bypass the BFF for client access.
- Keep secrets out of git; use environment variables.
- For transactional flows (inventory/payment), ensure idempotency and audit logs.


---

## Mapping to the architecture diagram
In the architecture diagram, this module corresponds to **GW (Integration Gateway)**:
- unified API entrypoint
- authentication & RBAC
- idempotency for inventory/payment
- logging/audit/trace_id propagation
- rate limiting

> Deploy location:
> - MVP can deploy GW together with the edge laptop or in the cloud.
> - If edge/offline becomes important, keep a thin edge GW and a cloud GW; both must follow the same API contracts.
