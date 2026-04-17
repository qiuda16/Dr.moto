# Document Output Guide

Updated: 2026-03-29

The backend now provides printable HTML documents for each work order.

## Supported Document Types

- `work-order`: Work Order Sheet
- `quote`: Quotation Sheet
- `pick-list`: Parts Pick List
- `delivery-note`: Delivery Note

## API

`GET /mp/workorders/{order_id}/documents/{doc_type}`

Example:

```http
GET /mp/workorders/f1b2937c-3af3-46ea-98f7-d9c204ef3071/documents/work-order
Authorization: Bearer <token>
```

Response is HTML (`text/html`) and can be:

- printed directly from browser
- saved as PDF using browser print dialog
- embedded in internal portal iframe

## Data Source

- Core header fields from BFF work order record.
- Financial and line details from Odoo (`drmoto.work.order` and `drmoto.work.order.line`).

## Operational Recommendation

- Freeze template style before store-wide rollout.
- Add store logo and legal footer in the HTML template function.
- For legally signed documents, keep a PDF snapshot in object storage and persist the file URL in DB.
