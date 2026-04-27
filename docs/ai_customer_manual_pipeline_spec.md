# AI Customer + Manual Ingest Unified Spec

Updated: 2026-04-26

## Goal

Use one chat entrypoint to serve both customer-side and staff-side workflows.
Manual AI parsing ingestion is executed as a controlled write pipeline under the same agent runtime.

## Entry API

- `POST /chat` (AI service)

Request:

```json
{
  "user_id": "u-001",
  "message": "parse manual and import to database",
  "context": {
    "model_id": 2237,
    "manual_job_id": 51,
    "confirm_write": true
  }
}
```

## Manual Ingest Trigger

Intent keywords (any):

- `维修手册`
- `手册识别`
- `导入手册`
- `manual ingest`
- `parse manual`
- `ocr manual`

## Write Confirmation Rule

Manual ingest is a high-risk write action.
The pipeline only executes when one of the following is true:

- `context.confirm_write = true`
- message includes explicit confirm phrases like `确认` / `开始导入`

If not confirmed, chat returns a confirmation-required response with `write_intent_detected`.

## Context Contract

### Required minimum

At least one of:

- `manual_job_id` or `parse_job_id`
- `document_id` (knowledge document id)
- (`model_id` + file source)

### File source options

- `manual_file_path` (file path visible to AI container)
- `manual_file_url` (fetchable URL)

### Optional metadata

- `manual_title`
- `manual_category` (default: `维修手册`)

## Pipeline Steps (Unified)

1. Upload manual (optional, if no existing document/job)
   - `POST /mp/knowledge/catalog-models/{model_id}/documents`
2. Start parse job (optional, if no existing job)
   - `POST /mp/knowledge/documents/{document_id}/parse`
3. Poll parse status
   - `GET /mp/knowledge/parse-jobs/{job_id}`
4. Bind catalog model
   - `POST /mp/knowledge/parse-jobs/{job_id}/bind-catalog-model`
5. Import specs
   - `POST /mp/knowledge/parse-jobs/{job_id}/import-confirmed-specs`
6. Materialize segments and procedures
   - `POST /mp/knowledge/parse-jobs/{job_id}/materialize-segments`
7. Sync service items from manual parts
   - `POST /mp/catalog/vehicle-models/{model_id}/service-items/sync-manual-parts`

## Async Rule

If parse does not finish within sync wait window:

- create runtime task `manual-ingest-{job_id}`
- return async status summary

## Chat Output Contract

### Success debug block

```json
{
  "debug": {
    "write_executed": true,
    "write_action": "manual_ingest_pipeline",
    "risk_level": "high",
    "manual_ingest": {
      "document_id": 334,
      "job_id": 51,
      "model_id": 2237,
      "imported_specs": 401,
      "materialized_segments": 1,
      "synced_service_items": 9
    }
  }
}
```

### Confirmation-required debug block

```json
{
  "debug": {
    "write_intent_detected": true,
    "write_action": "manual_ingest_pipeline",
    "requires_confirmation": true
  }
}
```

## Action Cards Contract

High-risk write tools must expose:

- `requires_confirmation: true`
- `blocked: true` when not yet confirmed

## Database Targets

Manual ingest should eventually write to:

- `vehicle_catalog_specs`
- `procedures`
- `procedure_steps`
- `vehicle_knowledge_segments`
- `vehicle_service_template_items`

## Isolation Rule

This project uses its own OpenClaw workspace/state:

- `/app/data/openclaw_drmoto_workspace`
- `/app/data/openclaw_drmoto_state`

No dependency on global `~/.openclaw` runtime is required.
