# MCP Team 6 — Events & Audit (EVT)

> Updated: 2025-12-17  
> Role: Immutable audit logs + event outbox backbone.

## Inputs
- `docs/security_baseline.md`
- `docs/test_acceptance.md`
- global rules

## Outputs
- audit_log schema + query APIs
- event_outbox/evt store schema (immutable)
- standardized event types
- retention/partition plan

## MUST
- append-only audit
- privileged actions require reason + audit
- outbox pattern to avoid lost events
