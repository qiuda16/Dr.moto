ALTER TABLE work_orders
    ADD CONSTRAINT uq_work_orders_uuid UNIQUE USING INDEX ix_work_orders_uuid;

ALTER TABLE vehicles
    ADD CONSTRAINT uq_vehicles_key UNIQUE USING INDEX ix_vehicles_key;

ALTER TABLE part_catalog_profiles
    ADD CONSTRAINT uq_part_catalog_profiles_part_id UNIQUE USING INDEX ix_part_catalog_profiles_part_id;

ALTER TABLE vehicle_service_template_profiles
    ADD CONSTRAINT uq_vehicle_service_template_profiles_template_item_id UNIQUE USING INDEX ix_vehicle_service_template_profiles_template_item_id;

ALTER TABLE work_order_process_records
    ADD CONSTRAINT uq_work_order_process_records_work_order_uuid UNIQUE USING INDEX ix_work_order_process_records_work_order_uuid;

ALTER TABLE work_order_delivery_checklists
    ADD CONSTRAINT uq_work_order_delivery_checklists_work_order_uuid UNIQUE USING INDEX ix_work_order_delivery_checklists_work_order_uuid;

ALTER TABLE work_order_advanced_profiles
    ADD CONSTRAINT uq_work_order_advanced_profiles_work_order_uuid UNIQUE USING INDEX ix_work_order_advanced_profiles_work_order_uuid;

ALTER TABLE part_catalog_profiles
    ADD CONSTRAINT fk_part_catalog_profiles_part_id
    FOREIGN KEY (part_id) REFERENCES part_catalog_items(id) ON DELETE CASCADE;

ALTER TABLE vehicle_catalog_specs
    ADD CONSTRAINT fk_vehicle_catalog_specs_model_id
    FOREIGN KEY (model_id) REFERENCES vehicle_catalog_models(id) ON DELETE CASCADE;

ALTER TABLE vehicle_service_template_items
    ADD CONSTRAINT fk_vehicle_service_template_items_model_id
    FOREIGN KEY (model_id) REFERENCES vehicle_catalog_models(id) ON DELETE CASCADE;

ALTER TABLE vehicle_service_template_profiles
    ADD CONSTRAINT fk_vehicle_service_template_profiles_template_item_id
    FOREIGN KEY (template_item_id) REFERENCES vehicle_service_template_items(id) ON DELETE CASCADE;

ALTER TABLE vehicle_service_template_parts
    ADD CONSTRAINT fk_vehicle_service_template_parts_template_item_id
    FOREIGN KEY (template_item_id) REFERENCES vehicle_service_template_items(id) ON DELETE CASCADE;

ALTER TABLE vehicle_service_template_parts
    ADD CONSTRAINT fk_vehicle_service_template_parts_part_id
    FOREIGN KEY (part_id) REFERENCES part_catalog_items(id) ON DELETE SET NULL;

ALTER TABLE vehicle_service_packages
    ADD CONSTRAINT fk_vehicle_service_packages_model_id
    FOREIGN KEY (model_id) REFERENCES vehicle_catalog_models(id) ON DELETE CASCADE;

ALTER TABLE vehicle_service_package_items
    ADD CONSTRAINT fk_vehicle_service_package_items_package_id
    FOREIGN KEY (package_id) REFERENCES vehicle_service_packages(id) ON DELETE CASCADE;

ALTER TABLE vehicle_service_package_items
    ADD CONSTRAINT fk_vehicle_service_package_items_template_item_id
    FOREIGN KEY (template_item_id) REFERENCES vehicle_service_template_items(id) ON DELETE CASCADE;

ALTER TABLE vehicle_knowledge_documents
    ADD CONSTRAINT fk_vehicle_knowledge_documents_model_id
    FOREIGN KEY (model_id) REFERENCES vehicle_catalog_models(id) ON DELETE CASCADE;

ALTER TABLE vehicle_knowledge_parse_jobs
    ADD CONSTRAINT fk_vehicle_knowledge_parse_jobs_document_id
    FOREIGN KEY (document_id) REFERENCES vehicle_knowledge_documents(id) ON DELETE CASCADE;

ALTER TABLE vehicle_knowledge_parse_jobs
    ADD CONSTRAINT fk_vehicle_knowledge_parse_jobs_model_id
    FOREIGN KEY (model_id) REFERENCES vehicle_catalog_models(id) ON DELETE CASCADE;

ALTER TABLE vehicle_knowledge_parse_pages
    ADD CONSTRAINT fk_vehicle_knowledge_parse_pages_job_id
    FOREIGN KEY (job_id) REFERENCES vehicle_knowledge_parse_jobs(id) ON DELETE CASCADE;

ALTER TABLE vehicle_knowledge_parse_pages
    ADD CONSTRAINT fk_vehicle_knowledge_parse_pages_document_id
    FOREIGN KEY (document_id) REFERENCES vehicle_knowledge_documents(id) ON DELETE CASCADE;

ALTER TABLE vehicle_knowledge_segments
    ADD CONSTRAINT fk_vehicle_knowledge_segments_model_id
    FOREIGN KEY (model_id) REFERENCES vehicle_catalog_models(id) ON DELETE CASCADE;

ALTER TABLE vehicle_knowledge_segments
    ADD CONSTRAINT fk_vehicle_knowledge_segments_source_document_id
    FOREIGN KEY (source_document_id) REFERENCES vehicle_knowledge_documents(id) ON DELETE CASCADE;

ALTER TABLE vehicle_knowledge_segments
    ADD CONSTRAINT fk_vehicle_knowledge_segments_source_job_id
    FOREIGN KEY (source_job_id) REFERENCES vehicle_knowledge_parse_jobs(id) ON DELETE CASCADE;

ALTER TABLE vehicle_knowledge_segments
    ADD CONSTRAINT fk_vehicle_knowledge_segments_segment_document_id
    FOREIGN KEY (segment_document_id) REFERENCES vehicle_knowledge_documents(id) ON DELETE SET NULL;

ALTER TABLE vehicle_knowledge_segments
    ADD CONSTRAINT fk_vehicle_knowledge_segments_procedure_id
    FOREIGN KEY (procedure_id) REFERENCES procedures(id) ON DELETE SET NULL;

ALTER TABLE procedure_steps
    ADD CONSTRAINT fk_procedure_steps_procedure_id
    FOREIGN KEY (procedure_id) REFERENCES procedures(id) ON DELETE CASCADE;

ALTER TABLE quotes
    ADD CONSTRAINT fk_quotes_work_order_uuid
    FOREIGN KEY (work_order_uuid) REFERENCES work_orders(uuid) ON DELETE CASCADE;

ALTER TABLE work_order_process_records
    ADD CONSTRAINT fk_work_order_process_records_work_order_uuid
    FOREIGN KEY (work_order_uuid) REFERENCES work_orders(uuid) ON DELETE CASCADE;

ALTER TABLE work_order_delivery_checklists
    ADD CONSTRAINT fk_work_order_delivery_checklists_work_order_uuid
    FOREIGN KEY (work_order_uuid) REFERENCES work_orders(uuid) ON DELETE CASCADE;

ALTER TABLE work_order_advanced_profiles
    ADD CONSTRAINT fk_work_order_advanced_profiles_work_order_uuid
    FOREIGN KEY (work_order_uuid) REFERENCES work_orders(uuid) ON DELETE CASCADE;

ALTER TABLE work_order_service_selections
    ADD CONSTRAINT fk_work_order_service_selections_work_order_uuid
    FOREIGN KEY (work_order_uuid) REFERENCES work_orders(uuid) ON DELETE CASCADE;

ALTER TABLE work_order_service_selections
    ADD CONSTRAINT fk_work_order_service_selections_template_item_id
    FOREIGN KEY (template_item_id) REFERENCES vehicle_service_template_items(id) ON DELETE SET NULL;

ALTER TABLE work_order_attachments
    ADD CONSTRAINT fk_work_order_attachments_work_order_uuid
    FOREIGN KEY (work_order_uuid) REFERENCES work_orders(uuid) ON DELETE CASCADE;
