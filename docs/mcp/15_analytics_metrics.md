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
