CREATE TABLE IF NOT EXISTS website_leads (
    id SERIAL PRIMARY KEY,
    store_id VARCHAR(255) NOT NULL DEFAULT 'default',
    name VARCHAR(255) NOT NULL,
    contact VARCHAR(255) NOT NULL,
    identity VARCHAR(255) NOT NULL DEFAULT 'rider',
    message VARCHAR(255),
    source_page VARCHAR(255),
    status VARCHAR(255) NOT NULL DEFAULT 'new',
    assigned_to VARCHAR(255),
    handled_by VARCHAR(255),
    handled_at TIMESTAMPTZ,
    converted_work_order_uuid VARCHAR(255),
    notes VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_website_leads_store_id ON website_leads(store_id);
CREATE INDEX IF NOT EXISTS idx_website_leads_status ON website_leads(status);
CREATE INDEX IF NOT EXISTS idx_website_leads_converted_work_order_uuid ON website_leads(converted_work_order_uuid);
CREATE UNIQUE INDEX IF NOT EXISTS uq_website_leads_converted_work_order_uuid
    ON website_leads(converted_work_order_uuid)
    WHERE converted_work_order_uuid IS NOT NULL;

CREATE TABLE IF NOT EXISTS work_order_offline_payments (
    id SERIAL PRIMARY KEY,
    store_id VARCHAR(255) NOT NULL DEFAULT 'default',
    work_order_uuid VARCHAR(255) NOT NULL,
    amount DOUBLE PRECISION NOT NULL,
    payment_method VARCHAR(255) NOT NULL,
    status VARCHAR(255) NOT NULL DEFAULT 'paid',
    payer_note VARCHAR(255),
    idempotency_key VARCHAR(255),
    received_by VARCHAR(255),
    received_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_work_order_offline_payments_store_id ON work_order_offline_payments(store_id);
CREATE INDEX IF NOT EXISTS idx_work_order_offline_payments_work_order_uuid ON work_order_offline_payments(work_order_uuid);
CREATE INDEX IF NOT EXISTS idx_work_order_offline_payments_status ON work_order_offline_payments(status);
CREATE UNIQUE INDEX IF NOT EXISTS uq_work_order_offline_payments_idempotency_key
    ON work_order_offline_payments(store_id, idempotency_key)
    WHERE idempotency_key IS NOT NULL;
