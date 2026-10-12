ALTER TABLE app_settings
    ADD COLUMN IF NOT EXISTS document_header_note VARCHAR(255),
    ADD COLUMN IF NOT EXISTS customer_document_footer_note VARCHAR(255),
    ADD COLUMN IF NOT EXISTS internal_document_footer_note VARCHAR(255),
    ADD COLUMN IF NOT EXISTS default_service_advice VARCHAR(255);

UPDATE app_settings
SET
    document_header_note = COALESCE(NULLIF(document_header_note, ''), '摩托车售后服务专业单据'),
    customer_document_footer_note = COALESCE(NULLIF(customer_document_footer_note, ''), '请客户核对维修项目、金额与交车说明后签字确认。'),
    internal_document_footer_note = COALESCE(NULLIF(internal_document_footer_note, ''), '用于门店内部留档、责任追溯与施工复核。'),
    default_service_advice = COALESCE(NULLIF(default_service_advice, ''), '建议客户按保养周期复检，并关注油液、制动与轮胎状态。');
