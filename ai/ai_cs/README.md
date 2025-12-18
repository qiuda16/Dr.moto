# AI Customer Service

## Purpose
RAG-based knowledge assistant + intent detection for customer service. Read-mostly; does not mutate transactional data.

## MVP endpoints
- `/chat`
- `/intent`
- `/search_kb`

## Rules
- Never directly write to Odoo or transactional DB.
- Any write action must be requested via BFF with RBAC and audit trail.
- Run asynchronously; tolerate external API failure without blocking core flows.

## Data sources
- Knowledge base (documents/FAQ/process).
- Optional read-only business data via BFF (no direct DB access).

## Deployment
- Run as an internal service.
- Use MQ for heavy/slow tasks if needed.
