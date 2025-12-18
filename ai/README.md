# AI Subsystems

## Purpose
AI customer service and future business AI (recommendations/analytics). Designed to be non-blocking to core transactions (async, read-mostly).

## Scope (MVP)
- ai_cs (RAG/intent/chat)
- ai_business (phase-2)

## Interfaces
- Exposes /chat, /intent, /search endpoints to cs_workspace and BFF.
- Reads KB and (optionally) read-only business data via BFF.

## Local development (high level)
1. Prepare knowledge base index.
1. Run AI service behind internal network; never let it write core transactions directly.

## Notes / Rules
- Do not bypass the BFF for client access.
- Keep secrets out of git; use environment variables.
- For transactional flows (inventory/payment), ensure idempotency and audit logs.
