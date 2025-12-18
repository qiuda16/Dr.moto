# MCP Team 7 — STAFF Web

> Updated: 2025-12-17  
> Role: Staff-facing UI for MVP operational flow.

## Inputs
- frozen OpenAPI
- RBAC matrix
- PRD flows

## Outputs
- WO board/list/detail
- diagnostics + quote editing
- issue/return flows (role-gated)
- payment close flows (cashier)
- error handling mapped to error codes

## MUST
- never rely on UI hiding for security
- retry-safe UX for idempotent actions
