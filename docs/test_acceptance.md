# MVP Acceptance Tests

> Date: 2025-12-17  
> Principle: **Auditability + Idempotency + Strong consistency** for inventory/payment.

## 1. Smoke Suite (must pass on every deploy)
### SMK-001 Odoo reachable
- Steps: Open Odoo web on configured URL
- Expected: Login page loads; DB available

### SMK-010 BFF health
- Steps: GET /health
- Expected: 200 with build info and trace_id

## 2. Critical Idempotency
### IDEM-INV-001 Issue parts twice
- Preconditions:
  - Work order in IN_PROGRESS
  - Product exists in Odoo with stock on hand
- Steps:
  1) POST /bo/workorders/{id}/issue with Idempotency-Key K
  2) Repeat the same request with Idempotency-Key K
- Expected:
  - Only one Odoo stock picking posted
  - BFF returns same result for both calls
  - Audit log contains 1 "ISSUE_POSTED" entry

### IDEM-PAY-001 WeChat callback twice
- Steps:
  1) Send valid callback payload for out_trade_no T
  2) Repeat the callback payload for T
- Expected:
  - Exactly one immutable payment record for T
  - Work order transitions to CLOSED once
  - Second call returns "already processed" (success response)

## 3. State Machine Integrity
### FSM-001 Closed work order cannot change price
- Steps:
  1) Close a work order
  2) Attempt to POST /bo/workorders/{id}/quote to change amounts
- Expected:
  - Returns WO_INVALID_STATE
  - Audit log records denied attempt

## 4. Reverse/Return flows
### REV-INV-001 Return after issue
- Steps:
  1) Issue part quantity 1
  2) Return quantity 1
- Expected:
  - Posted stock moves net to 0 on that item
  - Work order part line qty_issued=1, qty_returned=1

## 5. Media
### MED-001 Upload photo
- Steps:
  1) Call /media/presign
  2) Upload file to storage
  3) POST /workorders/{id}/media to save metadata
- Expected:
  - Work order media list shows the item
  - URL is stored; no binary stored in DB

## 6. Reporting
### RPT-001 Parts consumption based on posted moves
- Steps: Run parts consumption report for a day
- Expected: Numbers equal sum(posted stock moves), not plan lines
