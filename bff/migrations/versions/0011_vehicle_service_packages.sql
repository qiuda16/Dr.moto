CREATE TABLE IF NOT EXISTS vehicle_service_packages (
    id SERIAL PRIMARY KEY,
    model_id INTEGER NOT NULL,
    package_code VARCHAR(255),
    package_name VARCHAR(255) NOT NULL,
    description TEXT,
    recommended_interval_km INTEGER,
    recommended_interval_months INTEGER,
    labor_hours_total DOUBLE PRECISION,
    labor_price_total DOUBLE PRECISION,
    parts_price_total DOUBLE PRECISION,
    suggested_price_total DOUBLE PRECISION,
    sort_order INTEGER NOT NULL DEFAULT 100,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_vehicle_service_packages_model_id ON vehicle_service_packages(model_id);
CREATE INDEX IF NOT EXISTS idx_vehicle_service_packages_package_code ON vehicle_service_packages(package_code);
CREATE INDEX IF NOT EXISTS idx_vehicle_service_packages_is_active ON vehicle_service_packages(is_active);

CREATE TABLE IF NOT EXISTS vehicle_service_package_items (
    id SERIAL PRIMARY KEY,
    package_id INTEGER NOT NULL,
    template_item_id INTEGER NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 100,
    is_optional BOOLEAN NOT NULL DEFAULT FALSE,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_vehicle_service_package_items_package_id ON vehicle_service_package_items(package_id);
CREATE INDEX IF NOT EXISTS idx_vehicle_service_package_items_template_item_id ON vehicle_service_package_items(template_item_id);
