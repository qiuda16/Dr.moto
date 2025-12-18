# Data Model (Skeleton)

> Date: 2025-12-17

## Entities (Logical)
- shop
- employee
- customer
- vehicle
- work_order
- wo_labor_line
- wo_part_line
- wo_media
- wo_status_log
- payment
- audit_log
- idempotency_record

## Key Constraints
- (shop_id, phone) unique for customer
- (shop_id, plate_no) unique for vehicle
- idempotency_key unique for idempotency_record
- payment out_trade_no unique in payment ledger

## Partition Candidates (monthly)
- wo_status_log
- audit_log
- event_outbox (if used)
