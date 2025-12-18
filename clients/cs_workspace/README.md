# Customer Service Workspace

## Purpose
Agent workspace for handling inquiries, searching customers/work orders, and (optionally) using AI assistance.

## MVP features
- Agent login
- Conversation list (or integration placeholder)
- Customer & work order search
- Quick replies + knowledge base search
- AI assist (optional): intent + RAG answer + escalation

## Interfaces
- Calls BFF for customer/work order lookups
- Calls AI CS service for /chat and /search_kb (optional)

## Non-negotiables
- All operations go through **BFF** (no direct DB/Odoo).
- Use `trace_id` in requests where supported.
- For payment and inventory-related flows, ensure idempotency is respected.

## Run / Build
TBD (choose framework/tooling; keep it simple for MVP).
