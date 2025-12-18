# MCP Team 10 — Edge VID

> Updated: 2025-12-17  
> Role: RTSP/ONVIF ingest, local buffer, clip/frames, upload to OBJ.

## Inputs
- storage/obj policy
- edge boundaries

## Outputs
- clip API
- frame extraction API
- upload + metadata
- searchable index

## MUST
- retry-safe uploads; local buffering
- no writes to inventory/payment facts
