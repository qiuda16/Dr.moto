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
