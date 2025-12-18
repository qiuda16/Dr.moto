# Odoo Core & Custom Addons

## Purpose
Odoo Community base plus custom addons for repair domain (MRO). Holds all Odoo-side models, views, ACLs, and integration hooks.

## Scope (MVP)
- addons/drmoto_mro
- addons/drmoto_base (optional)
- docs/ for Odoo-related notes

## Interfaces
- Called by BFF via controlled integration API (RPC/REST wrapper).
- Owns inventory transactions and accounting postings.

## Local development (high level)
1. Mount ./addons into Odoo container at /mnt/extra-addons.
1. Update Apps List and install custom modules.

## Notes / Rules
- Do not bypass the BFF for client access.
- Keep secrets out of git; use environment variables.
- For transactional flows (inventory/payment), ensure idempotency and audit logs.
