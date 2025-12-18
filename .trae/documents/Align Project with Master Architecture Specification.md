I have analyzed your "Master Architecture & Boundaries" specification and compared it with the current project state. 

I will align the project with your **Global Architecture (0.1)** and **Data Truth (9.1)** rules.

## Execution Plan

### 1. Codify Architecture (Documentation)
- Create `docs/master_spec.md` to persist these non-negotiable rules as the project's "Bible".

### 2. BFF & Database Alignment (Section 5 & 9)
- **Refactor Models**: Update `bff/app/models.py` to include missing critical tables from Section 9.2:
    - `Quote` (Versioning for safety).
    - `AuditLog` (Append-only security).
    - `PaymentEvent` (Immutable ledger).
- **API Hardening**: Ensure `WorkOrder` state machine strictly follows Section 2.3.

### 3. Technician App "Real Logic" (Section 2)
- **Remove Mocks**: In `clients/mp_staff`, replace the mocked "Add Part" logic.
- **Integration**: Implement real Odoo Product Search & Work Order Line creation via BFF.

### 4. Create Display Terminal (Section 3)
- **New Client**: Initialize `clients/web_display` (Vue 3).
- **Features**: Implement the "Queue/Status Board" (Read-only, Auto-refresh) for the store big screen.

### 5. Deployment & Verification
- Ensure all 4 ends (Customer, Tech, Admin, Display) can launch.
- Verify the "Truth in Odoo" data flow.
