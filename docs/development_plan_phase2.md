# DrMoto Development Plan - Phase 2

**Date:** 2025-12-18
**Status:** Planning

## 1. Project Analysis

### 1.1 Current Structure
- **Monorepo Architecture**: Clean separation of concerns (`infra`, `bff`, `odoo`, `clients`).
- **Infrastructure**: Robust Docker Compose setup with all necessary services (DB, Redis, MinIO, Odoo).
- **Backend (BFF)**: Functional MVP with basic endpoints for Work Orders, Payments, and Ops.
- **ERP (Odoo)**: Custom module `drmoto_mro` installed with enhanced data models and rich UI views.
- **Clients**: 
  - `web_staff`: Prototype staff console.
  - `project_dashboard`: Functional documentation browser and requirement checker.

### 1.2 Code Quality & Debt
- **BFF (`bff/app/main.py`)**: Currently a monolithic file (~230 lines). Needs refactoring into modular routers.
- **Security**: **Critical Gap**. No authentication or authorization implementation yet. APIs are open.
- **Error Handling**: Basic. Needs a standardized global exception handler and structured error responses.
- **Testing**: **Critical Gap**. No automated tests for BFF or Odoo.
- **Odoo**: Good standard compliance. Views are well-structured.

### 1.3 Functional Gaps (vs PRD)
- **Inventory**: No integration for parts issue/return.
- **Payments**: No real payment gateway integration (only ledger recording).
- **Sync**: No mechanism for Odoo -> BFF updates (e.g., status changes initiated in Odoo).

---

## 2. Execution Plan

### Phase 2.1: Foundation Hardening (Next 3 Days)
*Goal: Secure the platform and improve maintainability.*

1.  **Refactor BFF Structure**:
    - Split `main.py` into `routers/` (`work_orders.py`, `payments.py`, `ops.py`, `auth.py`).
    - Move Pydantic models to `schemas/`.
2.  **Implement Security**:
    - Add `auth` router with Login endpoint (mock or DB-backed).
    - Implement JWT token generation and validation.
    - Add `get_current_user` dependency to protect sensitive endpoints.
3.  **Standardize Error Handling**:
    - Create a global exception handler to return JSON errors with `trace_id`.

### Phase 2.2: Core Logic Implementation (Next 5 Days)
*Goal: Complete the "Repair" loop.*

1.  **Inventory Integration**:
    - Implement `POST /mp/inventory/issue` in BFF.
    - Call Odoo `stock.picking` logic via XML-RPC.
    - Ensure idempotency using Redis keys.
2.  **Two-way Sync (Odoo -> BFF)**:
    - **Option A (Pull)**: BFF polls Odoo for status changes (Simple, less real-time).
    - **Option B (Push)**: Odoo `automated action` calls BFF webhook (Better). *Recommended*.
    - Implement `POST /callbacks/odoo/status_change` in BFF.

### Phase 2.3: Quality Assurance (Next 4 Days)
*Goal: Ensure reliability.*

1.  **BFF Testing**:
    - Install `pytest` and `httpx`.
    - Write unit tests for Work Order creation and Auth logic.
2.  **Odoo Testing**:
    - Add Python unit tests in `drmoto_mro/tests/`.
3.  **End-to-End Verification**:
    - Use the Staff Console to run a full flow: Create -> Assign -> Issue Parts -> Complete -> Pay.

---

## 3. Immediate Next Steps (Action Items)

1.  **[High]** Refactor `bff/app/main.py` to decouple concerns.
2.  **[High]** Implement JWT Authentication.
3.  **[Medium]** Add Inventory Issue endpoint.

## 4. Dependencies & Risks
- **Risk**: Odoo `stock` module complexity. *Mitigation*: Start with simple stock moves, ignore complex routing for now.
- **Risk**: BFF-Odoo Sync consistency. *Mitigation*: Master of record is Odoo; BFF is a view/proxy. Always fetch fresh state from Odoo when in doubt.
