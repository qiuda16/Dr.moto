ALTER TABLE work_orders ADD COLUMN IF NOT EXISTS store_id VARCHAR(64);
UPDATE work_orders SET store_id = 'default' WHERE store_id IS NULL;
ALTER TABLE work_orders ALTER COLUMN store_id SET NOT NULL;
CREATE INDEX IF NOT EXISTS idx_work_orders_store_id ON work_orders (store_id);

ALTER TABLE work_order_attachments ADD COLUMN IF NOT EXISTS store_id VARCHAR(64);
UPDATE work_order_attachments SET store_id = 'default' WHERE store_id IS NULL;
ALTER TABLE work_order_attachments ALTER COLUMN store_id SET NOT NULL;
CREATE INDEX IF NOT EXISTS idx_work_order_attachments_store_id ON work_order_attachments (store_id);

ALTER TABLE quotes ADD COLUMN IF NOT EXISTS store_id VARCHAR(64);
UPDATE quotes SET store_id = 'default' WHERE store_id IS NULL;
ALTER TABLE quotes ALTER COLUMN store_id SET NOT NULL;
CREATE INDEX IF NOT EXISTS idx_quotes_store_id ON quotes (store_id);

ALTER TABLE payment_ledger ADD COLUMN IF NOT EXISTS store_id VARCHAR(64);
UPDATE payment_ledger SET store_id = 'default' WHERE store_id IS NULL;
ALTER TABLE payment_ledger ALTER COLUMN store_id SET NOT NULL;
CREATE INDEX IF NOT EXISTS idx_payment_ledger_store_id ON payment_ledger (store_id);

ALTER TABLE payment_events ADD COLUMN IF NOT EXISTS store_id VARCHAR(64);
UPDATE payment_events SET store_id = 'default' WHERE store_id IS NULL;
ALTER TABLE payment_events ALTER COLUMN store_id SET NOT NULL;
CREATE INDEX IF NOT EXISTS idx_payment_events_store_id ON payment_events (store_id);

ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS store_id VARCHAR(64);
UPDATE audit_logs SET store_id = 'default' WHERE store_id IS NULL;
ALTER TABLE audit_logs ALTER COLUMN store_id SET NOT NULL;
CREATE INDEX IF NOT EXISTS idx_audit_logs_store_id ON audit_logs (store_id);

ALTER TABLE event_logs ADD COLUMN IF NOT EXISTS store_id VARCHAR(64);
UPDATE event_logs SET store_id = 'default' WHERE store_id IS NULL;
ALTER TABLE event_logs ALTER COLUMN store_id SET NOT NULL;
CREATE INDEX IF NOT EXISTS idx_event_logs_store_id ON event_logs (store_id);
