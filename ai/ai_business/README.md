# Business AI (Phase 2)

## Purpose
Recommendations and anomaly detection (parts usage, repeat repairs, suspicious refunds).

## MVP endpoints
- `(TBD)`

## Rules
- Use read-only exports or BFF read endpoints.
- All outputs are suggestions; humans confirm before applying.
- Keep models and features explainable for operations.

## Data sources
- Knowledge base (documents/FAQ/process).
- Optional read-only business data via BFF (no direct DB access).

## Deployment
- Run as an internal service.
- Use MQ for heavy/slow tasks if needed.
