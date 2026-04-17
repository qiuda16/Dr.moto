CREATE TABLE IF NOT EXISTS vehicle_health_records (
    id SERIAL PRIMARY KEY,
    store_id VARCHAR(64) NOT NULL DEFAULT 'default',
    customer_id VARCHAR(64) NOT NULL,
    vehicle_plate VARCHAR(64) NOT NULL,
    measured_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    odometer_km DOUBLE PRECISION NOT NULL,
    engine_rpm DOUBLE PRECISION NULL,
    battery_voltage DOUBLE PRECISION NULL,
    tire_front_psi DOUBLE PRECISION NULL,
    tire_rear_psi DOUBLE PRECISION NULL,
    coolant_temp_c DOUBLE PRECISION NULL,
    oil_life_percent DOUBLE PRECISION NULL,
    notes TEXT NULL,
    extra_json JSONB NULL,
    created_by VARCHAR(128) NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_vehicle_health_store_plate_time
    ON vehicle_health_records (store_id, vehicle_plate, measured_at DESC);

CREATE INDEX IF NOT EXISTS idx_vehicle_health_store_customer_time
    ON vehicle_health_records (store_id, customer_id, measured_at DESC);
