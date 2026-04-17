ALTER TABLE vehicle_knowledge_documents
    ADD COLUMN IF NOT EXISTS object_name VARCHAR(512);

CREATE TABLE IF NOT EXISTS vehicle_knowledge_parse_jobs (
    id BIGSERIAL PRIMARY KEY,
    document_id BIGINT NOT NULL,
    model_id BIGINT NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    provider VARCHAR(64),
    parser_version VARCHAR(64),
    page_count INTEGER,
    extracted_sections INTEGER,
    extracted_specs INTEGER,
    error_message TEXT,
    summary_json JSONB,
    raw_result_json JSONB,
    triggered_by VARCHAR(128),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_vehicle_knowledge_parse_jobs_document
    ON vehicle_knowledge_parse_jobs (document_id, id DESC);
CREATE INDEX IF NOT EXISTS idx_vehicle_knowledge_parse_jobs_model
    ON vehicle_knowledge_parse_jobs (model_id, id DESC);
CREATE INDEX IF NOT EXISTS idx_vehicle_knowledge_parse_jobs_status
    ON vehicle_knowledge_parse_jobs (status);

CREATE TABLE IF NOT EXISTS vehicle_knowledge_parse_pages (
    id BIGSERIAL PRIMARY KEY,
    job_id BIGINT NOT NULL,
    document_id BIGINT NOT NULL,
    page_number INTEGER NOT NULL,
    page_label VARCHAR(128),
    text_content TEXT,
    summary TEXT,
    blocks_json JSONB,
    specs_json JSONB,
    procedures_json JSONB,
    confidence DOUBLE PRECISION,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_vehicle_knowledge_parse_pages_job
    ON vehicle_knowledge_parse_pages (job_id, page_number ASC);
CREATE INDEX IF NOT EXISTS idx_vehicle_knowledge_parse_pages_document
    ON vehicle_knowledge_parse_pages (document_id, page_number ASC);
