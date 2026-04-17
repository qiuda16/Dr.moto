CREATE TABLE IF NOT EXISTS vehicle_catalog_specs (
    id SERIAL PRIMARY KEY,
    model_id INTEGER NOT NULL,
    spec_key TEXT NOT NULL,
    spec_label TEXT NOT NULL,
    spec_type TEXT,
    spec_value TEXT,
    spec_unit TEXT,
    source_page TEXT,
    source_text TEXT,
    review_status TEXT NOT NULL DEFAULT 'confirmed',
    source TEXT DEFAULT 'manual',
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_vehicle_catalog_specs_model_id
    ON vehicle_catalog_specs(model_id);

CREATE INDEX IF NOT EXISTS idx_vehicle_catalog_specs_spec_key
    ON vehicle_catalog_specs(spec_key);

CREATE INDEX IF NOT EXISTS idx_vehicle_catalog_specs_review_status
    ON vehicle_catalog_specs(review_status);
