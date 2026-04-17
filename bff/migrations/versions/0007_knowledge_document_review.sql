ALTER TABLE vehicle_knowledge_documents
    ADD COLUMN IF NOT EXISTS review_status TEXT;

ALTER TABLE vehicle_knowledge_documents
    ADD COLUMN IF NOT EXISTS review_notes TEXT;

ALTER TABLE vehicle_knowledge_documents
    ADD COLUMN IF NOT EXISTS reviewed_by TEXT;

ALTER TABLE vehicle_knowledge_documents
    ADD COLUMN IF NOT EXISTS reviewed_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_vehicle_knowledge_documents_review_status
    ON vehicle_knowledge_documents(review_status);
