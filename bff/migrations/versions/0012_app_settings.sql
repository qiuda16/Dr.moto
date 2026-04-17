CREATE TABLE IF NOT EXISTS app_settings (
    id SERIAL PRIMARY KEY,
    store_id VARCHAR(255) NOT NULL UNIQUE,
    store_name VARCHAR(255) NOT NULL DEFAULT '机车博士',
    brand_name VARCHAR(255) NOT NULL DEFAULT 'DrMoto',
    sidebar_badge_text VARCHAR(255),
    primary_color VARCHAR(32) NOT NULL DEFAULT '#409EFF',
    default_labor_price DOUBLE PRECISION,
    default_delivery_note TEXT,
    common_complaint_phrases_json JSON,
    updated_by VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_app_settings_store_id ON app_settings(store_id);
