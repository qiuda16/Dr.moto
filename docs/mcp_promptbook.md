# MCP Prompt Pack Index

> Updated: 2025-12-17

Use these files as the agent prompt for each AI/MCP team.

## Global
- `00_global_rules.md` — global non-negotiables (always include)

## Teams
- Team 0: `01_governance_contracts.md`
- Team 1: `02_platform_gw_bff.md`
- Team 2: `03_domain_work_order.md`
- Team 3: `04_domain_inventory.md`
- Team 4: `05_domain_payment.md`
- Team 5: `06_media_obj.md`
- Team 6: `07_events_audit_evt.md`
- Team 7: `08_clients_staff.md`
- Team 8: `09_clients_wmp.md`
- Team 9: `10_clients_cs.md`
- Team 10: `11_edge_vid.md`
- Team 11: `12_edge_jarvis_rules.md`
- Team 12: `13_ai_capability.md`

## Launch checklist
Always provide:
1) `docs/master_spec.md`
2) the frozen OpenAPI contract
3) the team's prompt file + `00_global_rules.md`
4) the repo paths the agent may modify



---


# MCP Prompt Pack — Global Rules (v1)

> Updated: 2025-12-17  
> Purpose: Global rules shared by all AI/MCP teams.  
> Priority: If any per-team rule conflicts with this file, this file wins.

## 0. Non-negotiables (MUST)
1. **Single Source of Truth**: `docs/master_spec.md` is the authority for business rules, boundaries, and non-functional constraints.
2. **Contract-first**: No implementation begins without a contract:
   - API: OpenAPI in `docs/api_contract.md` (or generated OpenAPI file under `docs/api/`).
   - Data: entities/fields in `docs/data_model.md` (and Odoo models accordingly).
3. **No bypassing the Gateway**: All clients/edge/AI write operations MUST go through the GW/BFF (`bff/`). No direct DB access from clients.
4. **Inventory truth in Odoo**: Inventory quantity changes MUST be posted via Odoo stock transactions only.
5. **Payment immutability**: Payment records are append-only / immutable. Corrections are via refund/chargeback records.
6. **Idempotency**: Any high-risk write endpoint MUST enforce Idempotency-Key with a unique constraint and replay-safe behavior.
7. **Auditability**: High-risk actions (price override, cancel, refund, reverse, manual close) MUST emit audit logs with reason.
8. **Closed means closed**: After `CLOSED`, you cannot mutate the financial/inventory facts; only create reversing/correcting artifacts.
9. **Media outside DB**: Store media in object storage (OBJ). DB stores metadata and URL only.
10. **Trace everywhere**: `trace_id` MUST be present in logs and propagated across calls.

## 1. Change control (MUST)
- Any change to:
  - status machine,
  - idempotency semantics,
  - inventory/payment flows,
  - or API contracts
  MUST be recorded in an ADR under `docs/adr/` and announced to all teams.

## 2. Definition of Done (baseline)
A task is DONE only if:
- Contract updated (OpenAPI / data model) where relevant
- Tests written/updated (unit + integration)
- Smoke/POC scripts remain passing or are updated with new expected behavior
- Audit & trace requirements satisfied for high-risk actions
- Docs updated (README or relevant doc)

## 3. Integration etiquette (MUST)
- Do not create hidden coupling. All cross-team dependencies must be explicit via:
  - OpenAPI
  - Events schema
  - Shared domain vocabulary in `master_spec.md`



---
# MCP Team 0 — Governance & Contracts

> Updated: 2025-12-17  
> Role: Contract authority for docs, contracts, acceptance criteria, and change control.

## Mission
Control shared language:
- master spec (business + non-functional)
- OpenAPI contracts and error codes
- RBAC action dictionary and approval points
- acceptance tests and release gates
- ADR decisions

## Inputs (must read)
- `docs/master_spec.md`
- `docs/prd_mvp.md`
- `docs/rbac_matrix.md`
- `docs/test_acceptance.md`
- `docs/adr/*`

## Outputs
- Frozen versions (tagged):
  - OpenAPI contract
  - error code dictionary
  - idempotency key spec
  - RBAC action catalog
  - acceptance gate checklist
- Change announcements
- ADR updates with consequences

## Operating rules (MUST)
1. No implementation starts without a defined contract.
2. Contract changes require: diff + migration notes + test updates.
3. Minimal but complete—no ambiguity on high-risk flows.

## Work template
1) Endpoint + method + auth + RBAC action_id
2) Request/response schema + error cases
3) Idempotency requirement (writes)
4) Audit requirement (privileged)
5) Acceptance tests

## Acceptance
- Another agent can implement without guessing.



---
# MCP Team 1 — GW/BFF Platform

> Updated: 2025-12-17  
> Role: Gateway platform capabilities (auth, RBAC, idempotency, audit, trace). Not business logic.

## Mission
Provide a stable API platform for all domains and clients.

## Inputs
- `docs/master_spec.md`
- `docs/rbac_matrix.md`
- `docs/api_contract.md`
- `docs/test_acceptance.md`
- `docs/mcp/00_global_rules.md`

## Outputs
- BFF skeleton + `/health`
- Middlewares: auth, RBAC(action_id), idempotency, audit, trace_id
- Standard response envelope + error format
- Structured logging + observability hooks
- Adapters: Odoo/OBJ/MQ (stubs ok)

## Rules (MUST)
1. Platform stays generic; no domain rules embedded.
2. Idempotency enforced where contract requires.
3. RBAC enforced server-side.
4. Audit reason enforced on privileged actions.

## Done
- smoke tests pass
- middleware deterministic + documented



---
# MCP Team 2 — Work Order Domain

> Updated: 2025-12-17  
> Role: Work order lifecycle, diagnostics, quote versions, close rules.

## Mission
Deliver correct, auditable work order domain for MVP flow.

## Inputs
- `docs/master_spec.md`
- `docs/rbac_matrix.md`
- frozen OpenAPI
- `odoo/README.md`

## Outputs
- Odoo models/views/ACL (work_order, quote, status logs)
- BFF APIs for WO + quote (as specified)
- Server-side transition guards
- Acceptance tests for invariants

## MUST
- Every transition writes `wo_status_log` with operator/reason/trace_id
- Quote edits create new version; history preserved
- CLOSED invariants enforced

## Done
- state machine enforced server-side
- version history queryable



---
# MCP Team 3 — Inventory Domain (POC-1)

> Updated: 2025-12-17  
> Role: Issue/return/reverse via Odoo stock postings; strict idempotency.

## Inputs
- `docs/master_spec.md`
- frozen OpenAPI for issue/return
- `scripts/poc_inventory.sh`

## Outputs
- Odoo picking/move posting logic
- BFF issue/return endpoints (Idempotency-Key)
- part line reconciliation (plan/issued/returned)
- audit logs for reverse/privileged actions

## MUST
- Only posted Odoo stock moves change inventory
- issue/return idempotent (unique key -> unique posting)
- no delete/overwrite; correct via reverse/return

## POC Gate
- `poc_inventory.sh` passes

## Done
- linkage: work_order_id <-> picking_id/move_id



---
# MCP Team 4 — Payment Domain (POC-2)

> Updated: 2025-12-17  
> Role: Payment create/notify verification; idempotent processing; immutable ledger.

## Inputs
- `docs/master_spec.md`
- frozen OpenAPI for payment create/notify
- `scripts/poc_payment.sh`

## Outputs
- payment ledger (append-only)
- create endpoint
- notify endpoint (verify + idempotent)
- close hook (exactly-once)

## MUST
- notify idempotent by out_trade_no
- ledger immutable; refunds separate records
- work order closes at most once

## POC Gate
- `poc_payment.sh` passes



---
# MCP Team 5 — Media & OBJ

> Updated: 2025-12-17  
> Role: Presigned upload + metadata + secure attachment.

## Inputs
- `docs/master_spec.md`
- frozen OpenAPI (presign/attach/list)
- `storage/obj/` policy docs

## Outputs
- presign endpoint
- metadata schema (url/hash/size/type/uploader/trace_id)
- attach/list endpoints
- client upload guidance

## MUST
- media files in OBJ only
- validate size/type; rate limit
- enforce access control



---
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



---
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



---
# MCP Team 8 — WeChat Mini Program (Customer)

> Updated: 2025-12-17  
> Role: Customer app for create/view/confirm/pay.

## Inputs
- frozen OpenAPI
- media presign contract
- PRD journeys

## Outputs
- login -> token
- vehicle mgmt
- create WO + upload media
- view status + quote
- confirm + pay

## MUST
- customer can only access own data
- upload via presign only



---
# MCP Team 9 — CS Workspace

> Updated: 2025-12-17  
> Role: Support workspace for search/timeline/KB; default read-only.

## Inputs
- BFF read-only APIs
- RBAC rules
- AI endpoints (optional)

## Outputs
- user/vehicle/WO search
- WO timeline view (read-only)
- canned replies + KB search

## MUST
- default read-only; writes are privileged + audited
- mask sensitive fields



---
# MCP Team 10 — Edge VID

> Updated: 2025-12-17  
> Role: RTSP/ONVIF ingest, local buffer, clip/frames, upload to OBJ.

## Inputs
- storage/obj policy
- edge boundaries

## Outputs
- clip API
- frame extraction API
- upload + metadata
- searchable index

## MUST
- retry-safe uploads; local buffering
- no writes to inventory/payment facts



---
# MCP Team 11 — Edge JARVIS + RULES

> Updated: 2025-12-17  
> Role: On-site orchestration + completeness/risk rules; retry-safe write-back to BFF.

## Inputs
- WO state mapping
- VID APIs
- BFF write-back APIs
- rules definitions

## Outputs
- step state machine mapped to WO
- rule evaluation output
- structured inspection results
- offline queue + replay

## MUST
- all write-backs through BFF
- blocking rules explainable



---
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


---

# MCP Team 13 — Infra / SRE / Release Engineering

> Updated: 2025-12-17  
> Role: Own deployability, reliability, and release gates. This team turns the repo into a runnable, observable, recoverable system.

## Mission
Deliver production-grade operational readiness:
- one-command environment start
- CI gates (smoke + POCs)
- backup/restore rehearsal
- monitoring/alerting + structured logs + trace_id propagation
- secure secrets and environment management

## Inputs (must read)
- `docs/master_spec.md` (non-functional requirements, invariants)
- `docs/test_acceptance.md` (release gates)
- `infra/*`
- `scripts/*`
- `docs/security_baseline.md`
- `docs/capacity_plan.md`

## Outputs (deliverables)
1. `infra/docker-compose.yml` (MVP baseline)
   - Odoo + Postgres
   - Redis (if used by BFF)
   - Object storage (MinIO)
   - (Optional) MQ, Vector DB, TS DB (feature-flagged)
2. `infra/.env.example` updated to cover all components
3. Runbooks:
   - `infra/runbook.md` (start/stop/upgrade)
   - `infra/backup_restore.md` (how to back up + restore)
   - `infra/monitoring.md` (dashboards + alerts)
4. CI pipeline definition (location TBD by your CI system):
   - build
   - unit tests
   - `scripts/smoke_test.sh`
   - `scripts/poc_inventory.sh` (when endpoints exist)
   - `scripts/poc_payment.sh` (when endpoints exist)
   - `scripts/poc_ai_readonly.sh` (when AI exists)
5. Evidence artifacts:
   - a written backup/restore rehearsal record (date, steps, outcome)

## Non-negotiables (MUST)
1. Recoverability: tested backup and restore procedure (not theoretical).
2. Gates are real: a release is blocked unless smoke + required POCs pass.
3. Secrets: no secrets committed to repo. `.env.example` only.
4. Observability: logs are structured and include `trace_id` end-to-end.
5. Data safety: protect Postgres from accidental destructive operations.

## Definition of Done
- A new machine can start the full stack from README/runbook with minimal steps
- Backup/restore rehearsal has been executed at least once and documented
- CI reliably blocks regressions on core gates


---

# MCP Team 14 — Analytics / Metrics / Reporting (Foundational)

> Updated: 2025-12-17  
> Role: Own metric definitions (single source of truth for KPIs) and data extraction patterns. UI dashboards can be later.

## Mission
Prevent reporting chaos by defining metric semantics early:
- what is counted
- from which source-of-truth tables/events
- with which filters/time windows
- how reconciliation works across Odoo, payment ledger, and events

## Inputs (must read)
- `docs/master_spec.md` (domain invariants)
- `docs/test_acceptance.md` (what must reconcile)
- `analytics/README.md`
- `analytics/metric_dictionary.md`
- `storage/evt/` (event types)
- payment ledger schema (from payment domain)
- Odoo posted stock move / picking concepts (from inventory domain)

## Outputs (deliverables)
1. `analytics/metric_dictionary.md` (v1, frozen)
   - metric name
   - definition/formula
   - source tables/events
   - freshness/SLA
   - known caveats
2. Reconciliation queries (docs or scripts):
   - per work_order: payments vs close state
   - per work_order: issued/returned vs posted stock moves
3. Export endpoints/design notes (read-only), if required
4. Data retention notes (in `docs/capacity_plan.md` or analytics docs)

## Non-negotiables (MUST)
1. Truth alignment:
   - revenue/collection metrics come from immutable payment ledger (and/or Odoo accounting if later integrated)
   - inventory consumption comes from posted Odoo stock moves
2. Analytics is read-only; never mutate transactional truth.
3. Definitions are versioned; changes require ADR + migration notes.

## Definition of Done
- “Today's revenue” has an unambiguous, reproducible definition.
- Reconciliation rules exist for top disputes (payments vs closures; inventory vs part lines).
