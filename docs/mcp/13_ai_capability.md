# MCP Team 12 — AI Capability (CS RAG + VEC)

> Updated: 2025-12-17  
> Role: AI chat + KB search + embeddings pipeline; strict read-only.

## Inputs
- `docs/master_spec.md`
- `storage/vec/`
- CS workspace needs

## Outputs
- `/search_kb`
- `/chat`
- ingestion + embedding pipeline
- optional `/intent`

## MUST
- no transactional write endpoints
- WO lookups via BFF read-only
- responses cite KB doc ids
