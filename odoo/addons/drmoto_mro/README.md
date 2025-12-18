# drmoto_mro

## Purpose
Custom Odoo addon for DrMoto.

## MVP responsibilities
- Define models, views, menus, and ACLs for the repair domain.
- Integrate with Odoo Stock for issue/return flows (inventory truth).

## Development rules
- Use Odoo ORM; do not update stock/accounting core tables directly.
- Keep migrations explicit when changing models.
- Ensure all critical actions are auditable (status logs) and idempotent where applicable.

## Install
1. Mount `odoo/addons` to Odoo container at `/mnt/extra-addons`.
2. Update Apps List in Odoo.
3. Install this module.

## Notes
This folder is a scaffold; module code will be generated in later steps.
