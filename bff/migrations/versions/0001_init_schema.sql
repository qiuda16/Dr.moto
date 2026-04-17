CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(255) PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS payment_ledger (
    id BIGSERIAL PRIMARY KEY,
    transaction_id VARCHAR(255) NOT NULL UNIQUE,
    work_order_id VARCHAR(255) NOT NULL,
    amount DOUBLE PRECISION NOT NULL,
    status VARCHAR(64) DEFAULT 'pending',
    provider VARCHAR(64) DEFAULT 'wechat',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_payment_ledger_work_order_id ON payment_ledger (work_order_id);
CREATE INDEX IF NOT EXISTS idx_payment_ledger_transaction_id ON payment_ledger (transaction_id);

CREATE TABLE IF NOT EXISTS payment_events (
    id BIGSERIAL PRIMARY KEY,
    provider_ref VARCHAR(255),
    raw_payload TEXT,
    signature_verified BOOLEAN DEFAULT FALSE,
    processing_status VARCHAR(64),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_payment_events_provider_ref ON payment_events (provider_ref);

CREATE TABLE IF NOT EXISTS audit_logs (
    id BIGSERIAL PRIMARY KEY,
    trace_id VARCHAR(255),
    actor_id VARCHAR(255),
    action VARCHAR(255) NOT NULL,
    target_entity VARCHAR(255),
    before_state JSONB,
    after_state JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_audit_logs_trace_id ON audit_logs (trace_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_actor_id ON audit_logs (actor_id);

CREATE TABLE IF NOT EXISTS quotes (
    id BIGSERIAL PRIMARY KEY,
    work_order_uuid VARCHAR(255) NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    items_json JSONB NOT NULL,
    amount_total DOUBLE PRECISION NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    status VARCHAR(64) DEFAULT 'draft',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by VARCHAR(255)
);
CREATE INDEX IF NOT EXISTS idx_quotes_work_order_uuid ON quotes (work_order_uuid);

CREATE TABLE IF NOT EXISTS work_order_attachments (
    id BIGSERIAL PRIMARY KEY,
    work_order_uuid VARCHAR(255) NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    file_url TEXT NOT NULL,
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_work_order_attachments_work_order_uuid ON work_order_attachments (work_order_uuid);

CREATE TABLE IF NOT EXISTS event_logs (
    id BIGSERIAL PRIMARY KEY,
    event_id VARCHAR(255) UNIQUE,
    event_type VARCHAR(255),
    source VARCHAR(64),
    payload TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_event_logs_event_id ON event_logs (event_id);
CREATE INDEX IF NOT EXISTS idx_event_logs_event_type ON event_logs (event_type);

CREATE TABLE IF NOT EXISTS work_orders (
    id BIGSERIAL PRIMARY KEY,
    uuid VARCHAR(255) NOT NULL UNIQUE,
    odoo_id INTEGER,
    customer_id VARCHAR(255) NOT NULL,
    vehicle_plate VARCHAR(64) NOT NULL,
    vehicle_key VARCHAR(255),
    description TEXT,
    status VARCHAR(64) DEFAULT 'draft',
    active_quote_version INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_work_orders_uuid ON work_orders (uuid);

CREATE TABLE IF NOT EXISTS vehicles (
    id BIGSERIAL PRIMARY KEY,
    key VARCHAR(255) NOT NULL UNIQUE,
    make VARCHAR(255) NOT NULL,
    model VARCHAR(255) NOT NULL,
    year_from INTEGER NOT NULL,
    year_to INTEGER,
    engine_code VARCHAR(255)
);
CREATE INDEX IF NOT EXISTS idx_vehicles_key ON vehicles (key);

CREATE TABLE IF NOT EXISTS procedures (
    id BIGSERIAL PRIMARY KEY,
    vehicle_key VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT
);
CREATE INDEX IF NOT EXISTS idx_procedures_vehicle_key ON procedures (vehicle_key);

CREATE TABLE IF NOT EXISTS procedure_steps (
    id BIGSERIAL PRIMARY KEY,
    procedure_id INTEGER NOT NULL,
    step_order INTEGER NOT NULL,
    instruction TEXT NOT NULL,
    required_tools TEXT,
    torque_spec TEXT,
    hazards TEXT
);
CREATE INDEX IF NOT EXISTS idx_procedure_steps_procedure_id ON procedure_steps (procedure_id);
