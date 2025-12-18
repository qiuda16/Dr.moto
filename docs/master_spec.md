# DrMoto Master Architecture & Boundaries
> "First set rules, then do functions"

## 0. Global Architecture & Boundaries
### 0.1 Roles & Ends
*   **Customer App (WeChat MP):** Submit requests, auth vehicle, view progress, confirm quote, pay, review.
*   **Technician App (WeChat MP / Pad Web):** Accept orders, diagnose, log labor/parts, evidence (photo/video), update nodes.
*   **Display Terminal (Store Screen):** No login/weak login, read-only "Queue, Progress, ETA".
*   **Admin Terminal (Store Manager/Front/Finance/Warehouse):** Scheduling, Quote Audit, Refund/Reverse, Inventory Ops (Odoo), Reconciliation.
*   **BFF:** Single Entry Point (Auth, Rate Limit, Idempotency, Audit, Aggregation).
*   **Odoo:** Inventory, Product, Stock Moves, Cost, Invoices ("Truth System").

### 0.2 Event Driven
*   "Work Order Status Change", "Payment Callback", "Stock Move" -> Domain Events (DB -> Outbox -> Async).
*   Avoid end-to-end strong coupling.

## 1. Customer App Design
### 1.1 MVP Loop
1.  **Login/Bind:** WeChat silent login + Phone.
2.  **Vehicle:** Add (VIN/Frame/Year) + Bind Store.
3.  **Work Order:** Create (Desc + Media + Booking).
4.  **Progress:** Timeline (Submitted -> Accepted -> Diagnosing -> Quote -> Repairing -> Pay -> Done).
5.  **Quote:** Show details (Labor, Parts, Tax) + **Version Control**.
6.  **Payment:** WeChat Pay + Invoice.
7.  **Review:** Star + Tag + Text.

### 1.2 Information Architecture
*   **Home:** Active Orders + "Quick Fix".
*   **Order:** List (Active/History) + Filter.
*   **Message:** Notifications.
*   **Profile:** Vehicle, Store, Info.

### 1.3 Stability Keys
*   **Weak Net:** Queue uploads, retry, no base64 large files.
*   **Idempotency:** Client generates UUID for Create/Confirm/Pay.
*   **Quote Version:** `quote_version` mismatch -> Block Payment.

## 2. Technician App Design
### 2.1 Core Workbench
*   **Inbox:** Filter by Store/Station/Skill.
*   **In Progress:** My Orders, Timer, Node Buttons.
*   **Diagnosis:** Codes/Conclusion/Advice (Templates).
*   **Evidence:** Photo/Video/Voice-to-Text.
*   **Parts Request:** Select Odoo Product + Qty -> Request.
*   **Completion:** Self-check checklist.

### 2.2 Auth & Risk
*   Tech updates *process*, not *money/inventory truth*.
*   "Request" -> Odoo Move (Confirmed by Warehouse/System).

### 2.3 State Machine
`SUBMITTED` -> `ACCEPTED` -> `DIAGNOSING` -> `QUOTED` -> `CUSTOMER_CONFIRMED` -> `REPAIRING` -> `READY_TO_PAY` -> `PAID` -> `CLOSED` / `CANCELED`

## 3. Display Terminal Design
### 3.1 Content
*   **Queue:** Ticket/Short ID (Masked) + Status + Station.
*   **ETA:** Range (e.g., 30-60 mins).
*   **Notice:** Store info.

### 3.2 Tech
*   Web SPA, Read-only BFF API.
*   Cache: 30-60s refresh.
*   Security: IP whitelist or Store Token.

## 4. Admin Terminal Design
### 4.1 Manager/Front
*   Scheduling, Quote Audit (Thresholds), Settlement.
### 4.2 Warehouse
*   Outbound (from Request), Inbound (Returns), Audit.
### 4.3 Finance
*   Payment Stream (Raw/Signed/Idempotent), Invoicing.

## 5. BFF / API Layer
### 5.1 Responsibilities
*   **Auth:** JWT/WeChat/Token.
*   **Resilience:** Rate Limit, Circuit Breaker.
*   **Idempotency:** Mandatory for write ops.
*   **Audit:** Who/When/What.
*   **Aggregation:** Odoo Objects -> Client DTOs.

### 5.2 Domains
*   `/mp/*` (Customer)
*   `/tech/*` (Tech)
*   `/admin/*` (Admin)
*   `/display/*` (Read-only)
*   `/webhooks/*` (Callbacks)

### 5.3 Schema Recommendations
*   `idempotency_keys`: (key, route, hash, response, status, created_at)
*   `audit_log`: Append-only (who, when, what, before, after, trace_id)
*   `payment_events`: Append-only (raw, verified, status)

## 6. Odoo Integration
### 6.1 Odoo Objects
*   Product, Inventory, Moves, Invoice/Sale.
### 6.2 Anti-Corruption
*   BFF Adapter (REST/XML-RPC).
*   Map Odoo errors to stable Error Codes.

## 7. AI Capabilities
*   **P0:** KB QA, Form Assist (RAG).
*   **P1:** Diagnosis Assist.
*   **P2:** Quality Check (Media/Checklist).
*   **Safety:** AI cannot write to Odoo/DB directly; must use BFF Tools.

## 8. Edge / IoT
*   Device Reg, Event Upstream.
*   Media: Upload Screenshot/Clip -> Object Storage -> BFF Index.
*   Bind Events to Work Orders.

## 9. Database & Storage
### 9.1 Truth Layering
*   **Odoo Postgres:** Inventory/Money Truth.
*   **BFF Postgres:** Users, Vehicles, WO Aggregates, Audit, Logs.

### 9.2 BFF Core Tables
*   `users`, `vehicles`, `work_orders`, `work_order_timeline`.
*   `quotes` (version, json, status).
*   `payments` (intent, amount, status).
*   `payment_events` (immutable).
*   `audit_log` (global).

## 10. Analytics
*   **Funnel:** Submit -> Pay.
*   **Efficiency:** Time metrics.
*   **Inventory:** Turns, Stockout.
*   **Path:** BFF Events -> Lightweight DW (PG View) -> Reports.
