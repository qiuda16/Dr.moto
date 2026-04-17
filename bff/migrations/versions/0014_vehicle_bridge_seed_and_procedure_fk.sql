-- Seed local vehicle bridge rows from standard catalog models so text-based
-- references like CATALOG_MODEL:<id> become real relational links.
INSERT INTO vehicles (key, make, model, year_from, year_to, engine_code)
SELECT
    'CATALOG_MODEL:' || m.id::text AS key,
    m.brand,
    m.model_name,
    m.year_from,
    m.year_to,
    m.default_engine_code
FROM vehicle_catalog_models m
WHERE NOT EXISTS (
    SELECT 1
    FROM vehicles v
    WHERE v.key = 'CATALOG_MODEL:' || m.id::text
);

ALTER TABLE procedures
DROP CONSTRAINT IF EXISTS fk_procedures_vehicle_key;

ALTER TABLE procedures
ADD CONSTRAINT fk_procedures_vehicle_key
FOREIGN KEY (vehicle_key) REFERENCES vehicles(key) ON DELETE CASCADE;
