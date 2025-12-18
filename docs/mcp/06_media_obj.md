# MCP Team 5 — Media & OBJ

> Updated: 2025-12-17  
> Role: Presigned upload + metadata + secure attachment.

## Inputs
- `docs/master_spec.md`
- frozen OpenAPI (presign/attach/list)
- `storage/obj/` policy docs

## Outputs
- presign endpoint
- metadata schema (url/hash/size/type/uploader/trace_id)
- attach/list endpoints
- client upload guidance

## MUST
- media files in OBJ only
- validate size/type; rate limit
- enforce access control
