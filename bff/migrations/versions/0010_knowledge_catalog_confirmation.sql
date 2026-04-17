ALTER TABLE vehicle_knowledge_documents
    ADD COLUMN IF NOT EXISTS catalog_confirmation_status VARCHAR(64) NOT NULL DEFAULT 'pending_confirmation';

ALTER TABLE vehicle_knowledge_documents
    ADD COLUMN IF NOT EXISTS catalog_candidate_json JSONB NULL;

ALTER TABLE vehicle_knowledge_documents
    ADD COLUMN IF NOT EXISTS catalog_confirmed_model_id INTEGER NULL;

ALTER TABLE vehicle_knowledge_documents
    ADD COLUMN IF NOT EXISTS catalog_confirmed_by VARCHAR(255) NULL;

ALTER TABLE vehicle_knowledge_documents
    ADD COLUMN IF NOT EXISTS catalog_confirmed_at TIMESTAMPTZ NULL;

CREATE INDEX IF NOT EXISTS idx_vehicle_knowledge_documents_catalog_confirmation_status
    ON vehicle_knowledge_documents (catalog_confirmation_status);

CREATE INDEX IF NOT EXISTS idx_vehicle_knowledge_documents_catalog_confirmed_model_id
    ON vehicle_knowledge_documents (catalog_confirmed_model_id);
