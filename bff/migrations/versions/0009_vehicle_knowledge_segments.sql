CREATE TABLE IF NOT EXISTS vehicle_knowledge_segments (
    id SERIAL PRIMARY KEY,
    model_id INTEGER NOT NULL,
    source_document_id INTEGER NOT NULL,
    source_job_id INTEGER NOT NULL,
    chapter_no VARCHAR(64) NULL,
    title VARCHAR(255) NOT NULL,
    start_page INTEGER NULL,
    end_page INTEGER NULL,
    segment_document_id INTEGER NULL,
    procedure_id INTEGER NULL,
    review_status VARCHAR(64) NOT NULL DEFAULT 'pending_review',
    notes TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NULL
);

CREATE INDEX IF NOT EXISTS idx_vehicle_knowledge_segments_model_id
    ON vehicle_knowledge_segments (model_id);

CREATE INDEX IF NOT EXISTS idx_vehicle_knowledge_segments_source_document_id
    ON vehicle_knowledge_segments (source_document_id);

CREATE INDEX IF NOT EXISTS idx_vehicle_knowledge_segments_source_job_id
    ON vehicle_knowledge_segments (source_job_id);

CREATE INDEX IF NOT EXISTS idx_vehicle_knowledge_segments_segment_document_id
    ON vehicle_knowledge_segments (segment_document_id);

CREATE INDEX IF NOT EXISTS idx_vehicle_knowledge_segments_procedure_id
    ON vehicle_knowledge_segments (procedure_id);

CREATE INDEX IF NOT EXISTS idx_vehicle_knowledge_segments_review_status
    ON vehicle_knowledge_segments (review_status);
