ALTER TABLE vehicle_knowledge_parse_jobs
    ADD COLUMN IF NOT EXISTS processed_batches INTEGER;

ALTER TABLE vehicle_knowledge_parse_jobs
    ADD COLUMN IF NOT EXISTS total_batches INTEGER;

ALTER TABLE vehicle_knowledge_parse_jobs
    ADD COLUMN IF NOT EXISTS progress_percent INTEGER;

ALTER TABLE vehicle_knowledge_parse_jobs
    ADD COLUMN IF NOT EXISTS progress_message TEXT;
