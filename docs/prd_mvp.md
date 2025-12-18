# PRD — MVP (DrMoto)

> Date: 2025-12-17  
> Owner: TBD  
> Status: Draft

## 1. Objectives
- Deliver a **stable, auditable, idempotent** repair workflow MVP that supports real store operations.
- Ensure **inventory truth** is managed by Odoo posted stock transactions.
- Ensure **payment truth** is managed by an immutable payment ledger (BFF) with WeChat callback idempotency.
- Support current **single shop / single warehouse**, while pre-building `shop_id` and `warehouse_id` for future expansion.

## 2. In-Scope (MVP)
### Customer / Vehicle
- Create/update customer (phone as primary identifier, dedupe rules).
- Create/update vehicle (plate_no required).

### Work Order Lifecycle
- Create work order (DRAFT -> CHECKIN).
- Record diagnosis (DIAGNOSING).
- Create quote versions (QUOTED) with labor and parts lines.
- Start repair (IN_PROGRESS).
- Mark ready (READY), deliver (DELIVERED), close (CLOSED).

### Inventory
- Issue parts (warehouse keeper posts stock picking in Odoo) with **idempotency**.
- Return parts (reverse flow) with **idempotency**.
- Work order parts lines track planned vs issued vs returned quantities.

### Payments
- Create WeChat payment order.
- Process WeChat callback with verification + **idempotency**.
- Record offline payment (manual) with audit trail.
- Close work order after successful payment/offline record.

### Media
- Upload photos/videos using **presigned upload**.
- Persist media metadata tied to work order.

### Reporting (MVP baseline)
- Work order counts by status and date.
- Payments by channel and date.
- Parts consumption based on posted stock moves.

### Observability & Audit
- Trace ID end-to-end.
- Status change logs (wo_status_log).
- Audit log for privileged actions (price changes, cancellations, refunds, stock issue/return).

## 3. Out-of-Scope (Explicitly NOT in MVP)
- Appointment scheduling, bay/shift planning.
- Membership, coupons, marketing campaigns.
- Multi-shop / multi-warehouse UI.
- Supplier price comparison and auto replenishment rules.
- Full invoicing/tax workflows (fields may be reserved).
- Advanced analytics warehouse/BI.

## 4. User Personas & Core Journeys
### 4.1 Customer (WeChat Mini-Program)
1) Login -> token  
2) Vehicle management  
3) Create service request / work order  
4) View progress -> confirm quote -> pay  
5) View history

### 4.2 Advisor / Front Desk
1) Create/check-in work order  
2) Record diagnosis  
3) Build quote version & request customer confirmation  
4) Coordinate with technician and keeper  
5) Deliver and hand-off to cashier

### 4.3 Technician
1) View assigned work orders  
2) Update repair progress  
3) Request parts issue (keeper posts)  
4) Mark ready

### 4.4 Warehouse Keeper
1) Review issue/return requests  
2) Post stock picking in Odoo  
3) Ensure idempotent execution  
4) Reconcile discrepancies (SOP)

### 4.5 Cashier
1) Trigger WeChat payment  
2) Confirm payment success  
3) Close work order  
4) Handle refund requests via SOP

## 5. Functional Requirements (User Stories)
> Each story MUST have acceptance criteria. Keep IDs stable.

### WO-001 Create Work Order
- As an advisor/customer, I can create a new work order with customer + vehicle + symptom description.
**Acceptance Criteria**
- A work order ID and number are generated.
- Status is `DRAFT` or `CHECKIN` per flow.
- `shop_id` is assigned (default).

### WO-010 Quote Versioning
- As an advisor, I can create a quote version containing labor lines and part lines.
**Acceptance Criteria**
- New version increments `quotation_version`.
- Previous versions remain readable and immutable.

### INV-001 Issue Parts (Idempotent)
- As a keeper, I can issue parts for a work order; repeated requests with same idempotency key do not duplicate.
**Acceptance Criteria**
- Only one Odoo posted stock picking exists for a given idempotency key.
- Work order part line `qty_issued` matches posted move quantities.

### PAY-001 WeChat Callback (Idempotent)
- As the system, I process WeChat payment callback; repeated callbacks do not duplicate payment entries.
**Acceptance Criteria**
- Exactly one immutable payment record for the same out_trade_no.
- Work order closes only once.

(Add more stories in `docs/test_acceptance.md`.)

## 6. Non-Functional Requirements
- Availability: MVP target 99.5% (dev/stage may be lower).
- Data durability: daily backups; restore drill successful.
- Security: least privilege RBAC; sensitive data masked in logs.
- Performance: payment callback must respond quickly; heavy tasks async.

## 7. Dependencies
- Odoo + Postgres running and reachable.
- BFF configured with Odoo integration credentials.
- WeChat app credentials & payment config.
- Object storage credentials.

## 8. Risks
- Incorrect stock reconciliation if bypassing Odoo transactions.
- Payment callback storms without idempotency.
- Quote change disputes without immutable history.

## 9. Open Questions (to be resolved)
- Whether to implement staff console separately or rely on Odoo UI for MVP.
- Which MQ technology to use for MVP.
