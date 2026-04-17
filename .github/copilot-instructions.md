# DrMoto Project Instructions

## Project Overview
DrMoto is a vehicle maintenance management system built as a monorepo with multiple services:
- **BFF (Backend for Frontend)**: FastAPI service handling business logic, Odoo integration, and external APIs
- **AI Service**: FastAPI service for customer service AI assistants and knowledge base
- **Clients**: Vue.js WeChat mini-programs for customers and staff
- **Odoo**: ERP system as single source of truth for inventory and accounting
- **Infrastructure**: Docker-based deployment with monitoring, backups, and operational scripts

Key principles: No direct client DB access, idempotency for critical operations, auditability, and event-driven architecture.

## Key Conventions
- **Backend (Python/FastAPI)**: PascalCase for models, snake_case for functions, relative imports within app, explicit dependency injection
- **Frontend (Vue.js)**: Vue 3 Composition API, Pinia for state management, Vant UI components, Axios for HTTP
- **Idempotency**: Use UUID-based request deduplication for inventory mutations and payments
- **Audit Logging**: Automatic logging of privileged actions with timestamps
- **Event Emission**: Async event publishing for state changes
- **Naming**: Consistent across services (WorkOrder, VehicleHealthRecord, etc.)

## Build and Test Commands
- **Python Services**: `pip install -r requirements.txt`, run with `uvicorn app.main:app --reload` (dev) or via Docker
- **Frontend**: `npm install`, `npm run dev` (Vite), `npm run build`
- **Infrastructure**: Use PowerShell scripts in `scripts/` for operations (e.g., `.\scripts\preflight_prod.ps1`)
- **Testing**: Integration-focused smoke tests (`smoke_test.ps1`), acceptance tests (`mp_customer_acceptance.ps1`), health checks via `/health` endpoints

## Architecture and Boundaries
- **BFF owns**: External API contracts, business rules, integrations, idempotency
- **Odoo owns**: ERP logic, inventory mutations, accounting postings
- **AI services**: Isolated, read-mostly, non-critical path
- **Clients**: Thin presentation layers calling BFF only
- Critical flows: Issue parts (BFF → Odoo → event), Payments (BFF → WeChat → callback → idempotent close)

See [docs/architecture.md](docs/architecture.md) for detailed architecture and non-negotiables.

## Common Pitfalls
- **Connection Issues**: Remote drops, Odoo connectivity - ensure services are reachable
- **Configuration**: Change default secrets, disable dev flags in production, validate with `validate_prod_env.ps1`
- **Database**: Odoo module installation, migration version conflicts, store isolation
- **Environment Setup**: Start infra first, ensure compatible Python/Node versions
- **Operations**: Monitor health endpoints, use backup/restore scripts, run failure drills

See [docs/production_sop_final.md](docs/production_sop_final.md) and [docs/resilience_drill_playbook.md](docs/resilience_drill_playbook.md) for operational guidance.

## Links to Documentation
- [Master Specification](docs/master_spec.md)
- [API Contract](docs/api_contract.md)
- [Data Model](docs/data_model.md)
- [RBAC Matrix](docs/rbac_matrix.md)
- [Go-Live Checklist](docs/go_live_checklist.md)
- [Security Baseline](docs/security_baseline.md)
- [Release Notes](docs/release_notes_20260329.md)