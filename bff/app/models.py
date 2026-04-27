from sqlalchemy import Boolean, Column, DateTime, Float, Integer, JSON, String
from sqlalchemy.sql import func

from .core.db import Base


class PaymentLedger(Base):
    __tablename__ = "payment_ledger"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(String(255), unique=True, index=True, nullable=False)
    store_id = Column(String(255), index=True, nullable=False, default="default")
    work_order_id = Column(String(255), index=True, nullable=False)
    amount = Column(Float, nullable=False)
    status = Column(String(255), default="pending")
    provider = Column(String(255), default="wechat")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class PaymentEvent(Base):
    __tablename__ = "payment_events"

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(String(255), index=True, nullable=False, default="default")
    provider_ref = Column(String(255), index=True)
    raw_payload = Column(String(255))
    signature_verified = Column(Boolean, default=False)
    processing_status = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(String(255), index=True, nullable=False, default="default")
    trace_id = Column(String(255), index=True, nullable=True)
    actor_id = Column(String(255), index=True)
    action = Column(String(255), nullable=False)
    target_entity = Column(String(255))
    before_state = Column(JSON, nullable=True)
    after_state = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AppSetting(Base):
    __tablename__ = "app_settings"

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(String(255), index=True, nullable=False, unique=True, default="default")
    store_name = Column(String(255), nullable=False, default="机车博士")
    brand_name = Column(String(255), nullable=False, default="DrMoto")
    sidebar_badge_text = Column(String(255), nullable=True, default="门店管理")
    primary_color = Column(String(32), nullable=False, default="#409EFF")
    default_labor_price = Column(Float, nullable=True, default=80)
    default_delivery_note = Column(String(255), nullable=True)
    document_header_note = Column(String(255), nullable=True)
    customer_document_footer_note = Column(String(255), nullable=True)
    internal_document_footer_note = Column(String(255), nullable=True)
    default_service_advice = Column(String(255), nullable=True)
    common_complaint_phrases_json = Column(JSON, nullable=True)
    updated_by = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class StaffAccount(Base):
    __tablename__ = "staff_accounts"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    email = Column(String(255), nullable=True)
    role = Column(String(64), nullable=False, default="staff", index=True)
    disabled = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Quote(Base):
    __tablename__ = "quotes"

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(String(255), index=True, nullable=False, default="default")
    work_order_uuid = Column(String(255), index=True, nullable=False)
    version = Column(Integer, nullable=False, default=1)
    items_json = Column(JSON, nullable=False)
    amount_total = Column(Float, nullable=False)
    is_active = Column(Boolean, default=True)
    status = Column(String(255), default="draft")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(String(255), nullable=True)


class WorkOrderAttachment(Base):
    __tablename__ = "work_order_attachments"

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(String(255), index=True, nullable=False, default="default")
    work_order_uuid = Column(String(255), index=True, nullable=False)
    file_name = Column(String(255), nullable=False)
    file_url = Column(String(255), nullable=False)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())


class EventLog(Base):
    __tablename__ = "event_logs"

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(String(255), index=True, nullable=False, default="default")
    event_id = Column(String(255), unique=True, index=True)
    event_type = Column(String(255), index=True)
    source = Column(String(255))
    payload = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class WorkOrder(Base):
    __tablename__ = "work_orders"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(255), unique=True, index=True, nullable=False)
    store_id = Column(String(255), index=True, nullable=False, default="default")
    odoo_id = Column(Integer, nullable=True)
    customer_id = Column(String(255), nullable=False)
    vehicle_plate = Column(String(255), nullable=False)
    vehicle_key = Column(String(255), nullable=True)
    description = Column(String(255), nullable=True)
    status = Column(String(255), default="draft")
    active_quote_version = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class WorkOrderProcessRecord(Base):
    __tablename__ = "work_order_process_records"

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(String(255), index=True, nullable=False, default="default")
    work_order_uuid = Column(String(255), index=True, unique=True, nullable=False)
    symptom_draft = Column(String(255), nullable=True)
    symptom_confirmed = Column(String(255), nullable=True)
    quick_check_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Vehicle(Base):
    __tablename__ = "vehicles"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(255), unique=True, index=True, nullable=False)
    make = Column(String(255), nullable=False)
    model = Column(String(255), nullable=False)
    year_from = Column(Integer, nullable=False)
    year_to = Column(Integer, nullable=True)
    engine_code = Column(String(255), nullable=True)


class Procedure(Base):
    __tablename__ = "procedures"

    id = Column(Integer, primary_key=True, index=True)
    vehicle_key = Column(String(255), index=True, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(String(255))


class ProcedureStep(Base):
    __tablename__ = "procedure_steps"

    id = Column(Integer, primary_key=True, index=True)
    procedure_id = Column(Integer, nullable=False, index=True)
    step_order = Column(Integer, nullable=False)
    instruction = Column(String(255), nullable=False)
    required_tools = Column(String(255))
    torque_spec = Column(String(255))
    hazards = Column(String(255))


class VehicleHealthRecord(Base):
    __tablename__ = "vehicle_health_records"

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(String(255), index=True, nullable=False, default="default")
    customer_id = Column(String(255), index=True, nullable=False)
    vehicle_plate = Column(String(255), index=True, nullable=False)
    measured_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    odometer_km = Column(Float, nullable=False)
    engine_rpm = Column(Float, nullable=True)
    battery_voltage = Column(Float, nullable=True)
    tire_front_psi = Column(Float, nullable=True)
    tire_rear_psi = Column(Float, nullable=True)
    coolant_temp_c = Column(Float, nullable=True)
    oil_life_percent = Column(Float, nullable=True)
    notes = Column(String(255), nullable=True)
    extra_json = Column(JSON, nullable=True)
    created_by = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class VehicleCatalogModel(Base):
    __tablename__ = "vehicle_catalog_models"

    id = Column(Integer, primary_key=True, index=True)
    brand = Column(String(255), index=True, nullable=False)
    model_name = Column(String(255), index=True, nullable=False)
    year_from = Column(Integer, nullable=False)
    year_to = Column(Integer, nullable=True)
    displacement_cc = Column(Integer, nullable=True)
    category = Column(String(255), nullable=True)
    fuel_type = Column(String(255), nullable=True, default="gasoline")
    default_engine_code = Column(String(255), nullable=True)
    source = Column(String(255), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class VehicleCatalogSpec(Base):
    __tablename__ = "vehicle_catalog_specs"

    id = Column(Integer, primary_key=True, index=True)
    model_id = Column(Integer, index=True, nullable=False)
    spec_key = Column(String(255), index=True, nullable=False)
    spec_label = Column(String(255), nullable=False)
    spec_type = Column(String(255), nullable=True)
    spec_value = Column(String(255), nullable=True)
    spec_unit = Column(String(255), nullable=True)
    source_page = Column(String(255), nullable=True)
    source_text = Column(String(255), nullable=True)
    review_status = Column(String(255), nullable=False, default="confirmed", index=True)
    source = Column(String(255), nullable=True, default="manual")
    notes = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class PartCatalogItem(Base):
    __tablename__ = "part_catalog_items"

    id = Column(Integer, primary_key=True, index=True)
    part_no = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(255), index=True, nullable=False)
    brand = Column(String(255), nullable=True)
    category = Column(String(255), index=True, nullable=True)
    unit = Column(String(255), nullable=False, default="unit")
    compatible_model_ids = Column(JSON, nullable=True)
    min_stock = Column(Float, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class PartCatalogProfile(Base):
    __tablename__ = "part_catalog_profiles"

    id = Column(Integer, primary_key=True, index=True)
    part_id = Column(Integer, index=True, unique=True, nullable=False)
    sale_price = Column(Float, nullable=True)
    cost_price = Column(Float, nullable=True)
    stock_qty = Column(Float, nullable=True)
    supplier_name = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class VehicleServiceTemplateItem(Base):
    __tablename__ = "vehicle_service_template_items"

    id = Column(Integer, primary_key=True, index=True)
    model_id = Column(Integer, index=True, nullable=False)
    part_name = Column(String(255), nullable=False)
    part_code = Column(String(255), nullable=True)
    repair_method = Column(String(255), nullable=True)
    labor_hours = Column(Float, nullable=True)
    notes = Column(String(255), nullable=True)
    sort_order = Column(Integer, nullable=False, default=100)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class VehicleServiceTemplateProfile(Base):
    __tablename__ = "vehicle_service_template_profiles"

    id = Column(Integer, primary_key=True, index=True)
    template_item_id = Column(Integer, index=True, unique=True, nullable=False)
    labor_price = Column(Float, nullable=True)
    suggested_price = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class VehicleServiceTemplatePart(Base):
    __tablename__ = "vehicle_service_template_parts"

    id = Column(Integer, primary_key=True, index=True)
    template_item_id = Column(Integer, index=True, nullable=False)
    part_id = Column(Integer, index=True, nullable=True)
    part_no = Column(String(255), nullable=True)
    part_name = Column(String(255), nullable=False)
    qty = Column(Float, nullable=False, default=1)
    unit_price = Column(Float, nullable=True)
    notes = Column(String(255), nullable=True)
    sort_order = Column(Integer, nullable=False, default=100)
    is_optional = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class WorkOrderServiceSelection(Base):
    __tablename__ = "work_order_service_selections"

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(String(255), index=True, nullable=False, default="default")
    work_order_uuid = Column(String(255), index=True, nullable=False)
    template_item_id = Column(Integer, index=True, nullable=True)
    service_name = Column(String(255), nullable=False)
    service_code = Column(String(255), nullable=True)
    repair_method = Column(String(255), nullable=True)
    labor_hours = Column(Float, nullable=True)
    labor_price = Column(Float, nullable=True)
    suggested_price = Column(Float, nullable=True)
    notes = Column(String(255), nullable=True)
    required_parts_json = Column(JSON, nullable=True)
    sort_order = Column(Integer, nullable=False, default=100)
    created_by = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class VehicleKnowledgeDocument(Base):
    __tablename__ = "vehicle_knowledge_documents"

    id = Column(Integer, primary_key=True, index=True)
    model_id = Column(Integer, index=True, nullable=False)
    title = Column(String(255), nullable=False)
    file_name = Column(String(255), nullable=False)
    object_name = Column(String(255), nullable=True)
    file_url = Column(String(255), nullable=False)
    file_type = Column(String(255), nullable=True)
    category = Column(String(255), nullable=True)
    notes = Column(String(255), nullable=True)
    review_status = Column(String(255), nullable=True, index=True)
    review_notes = Column(String(255), nullable=True)
    reviewed_by = Column(String(255), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    catalog_confirmation_status = Column(String(255), nullable=False, default="pending_confirmation", index=True)
    catalog_candidate_json = Column(JSON, nullable=True)
    catalog_confirmed_model_id = Column(Integer, index=True, nullable=True)
    catalog_confirmed_by = Column(String(255), nullable=True)
    catalog_confirmed_at = Column(DateTime(timezone=True), nullable=True)
    uploaded_by = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class VehicleKnowledgeParseJob(Base):
    __tablename__ = "vehicle_knowledge_parse_jobs"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, index=True, nullable=False)
    model_id = Column(Integer, index=True, nullable=False)
    status = Column(String(255), nullable=False, default="pending", index=True)
    provider = Column(String(255), nullable=True)
    parser_version = Column(String(255), nullable=True)
    page_count = Column(Integer, nullable=True)
    extracted_sections = Column(Integer, nullable=True)
    extracted_specs = Column(Integer, nullable=True)
    processed_batches = Column(Integer, nullable=True)
    total_batches = Column(Integer, nullable=True)
    progress_percent = Column(Integer, nullable=True)
    progress_message = Column(String(255), nullable=True)
    error_message = Column(String(255), nullable=True)
    summary_json = Column(JSON, nullable=True)
    raw_result_json = Column(JSON, nullable=True)
    triggered_by = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)


class VehicleKnowledgeParsePage(Base):
    __tablename__ = "vehicle_knowledge_parse_pages"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, index=True, nullable=False)
    document_id = Column(Integer, index=True, nullable=False)
    page_number = Column(Integer, nullable=False)
    page_label = Column(String(255), nullable=True)
    text_content = Column(String(255), nullable=True)
    summary = Column(String(255), nullable=True)
    blocks_json = Column(JSON, nullable=True)
    specs_json = Column(JSON, nullable=True)
    procedures_json = Column(JSON, nullable=True)
    confidence = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class VehicleKnowledgeSegment(Base):
    __tablename__ = "vehicle_knowledge_segments"

    id = Column(Integer, primary_key=True, index=True)
    model_id = Column(Integer, index=True, nullable=False)
    source_document_id = Column(Integer, index=True, nullable=False)
    source_job_id = Column(Integer, index=True, nullable=False)
    chapter_no = Column(String(255), nullable=True)
    title = Column(String(255), nullable=False)
    start_page = Column(Integer, nullable=True)
    end_page = Column(Integer, nullable=True)
    segment_document_id = Column(Integer, index=True, nullable=True)
    procedure_id = Column(Integer, index=True, nullable=True)
    review_status = Column(String(255), nullable=False, default="pending_review", index=True)
    notes = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class WorkOrderDeliveryChecklist(Base):
    __tablename__ = "work_order_delivery_checklists"

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(String(255), index=True, nullable=False, default="default")
    work_order_uuid = Column(String(255), index=True, unique=True, nullable=False)
    explained_to_customer = Column(Boolean, nullable=False, default=False)
    returned_old_parts = Column(Boolean, nullable=False, default=False)
    next_service_notified = Column(Boolean, nullable=False, default=False)
    payment_confirmed = Column(Boolean, nullable=False, default=False)
    payment_method = Column(String(255), nullable=True)
    payment_amount = Column(Float, nullable=True)
    notes = Column(String(255), nullable=True)
    updated_by = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class WorkOrderAdvancedProfile(Base):
    __tablename__ = "work_order_advanced_profiles"

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(String(255), index=True, nullable=False, default="default")
    work_order_uuid = Column(String(255), index=True, unique=True, nullable=False)
    assigned_technician = Column(String(255), nullable=True)
    service_bay = Column(String(255), nullable=True)
    priority = Column(String(255), nullable=True)
    promised_at = Column(DateTime(timezone=True), nullable=True)
    estimated_finish_at = Column(DateTime(timezone=True), nullable=True)
    is_rework = Column(Boolean, nullable=False, default=False)
    is_urgent = Column(Boolean, nullable=False, default=False)
    qc_owner = Column(String(255), nullable=True)
    internal_notes = Column(String(255), nullable=True)
    updated_by = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class CustomerWechatBinding(Base):
    __tablename__ = "customer_wechat_bindings"

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(String(255), index=True, nullable=False, default="default")
    partner_id = Column(Integer, index=True, nullable=False)
    openid = Column(String(255), index=True, nullable=False)
    unionid = Column(String(255), index=True, nullable=True)
    phone = Column(String(255), nullable=True)
    is_primary = Column(Boolean, nullable=False, default=True)
    status = Column(String(255), nullable=False, default="active")
    bound_at = Column(DateTime(timezone=True), server_default=func.now())
    unbound_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class CustomerAuthSession(Base):
    __tablename__ = "customer_auth_sessions"

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(String(255), index=True, nullable=False, default="default")
    partner_id = Column(Integer, index=True, nullable=False)
    binding_id = Column(Integer, index=True, nullable=False)
    session_token_hash = Column(String(255), index=True, nullable=False, unique=True)
    refresh_token_hash = Column(String(255), index=True, nullable=True, unique=True)
    expires_at = Column(DateTime(timezone=True), index=True, nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    device_id = Column(String(255), nullable=True)
    device_type = Column(String(255), nullable=True)
    ip = Column(String(255), nullable=True)
    user_agent = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class CustomerSubscriptionPref(Base):
    __tablename__ = "customer_subscription_prefs"

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(String(255), index=True, nullable=False, default="default")
    partner_id = Column(Integer, index=True, nullable=False)
    vehicle_id = Column(Integer, index=True, nullable=True)
    notify_enabled = Column(Boolean, nullable=False, default=True)
    remind_before_days = Column(Integer, nullable=False, default=7)
    remind_before_km = Column(Integer, nullable=False, default=500)
    prefer_channel = Column(String(255), nullable=False, default="wechat_subscribe")
    last_notified_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class CustomerAppointmentDraft(Base):
    __tablename__ = "customer_appointment_drafts"

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(String(255), index=True, nullable=False, default="default")
    partner_id = Column(Integer, index=True, nullable=False)
    vehicle_id = Column(Integer, index=True, nullable=True)
    vehicle_plate = Column(String(255), nullable=True)
    subject = Column(String(255), nullable=False)
    service_kind = Column(String(255), nullable=True)
    source = Column(String(255), nullable=True, default="mini_program")
    preferred_date = Column(DateTime(timezone=True), nullable=True)
    notes = Column(String(255), nullable=True)
    payload = Column(JSON, nullable=True)
    status = Column(String(255), nullable=False, default="draft")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class VehicleServicePackage(Base):
    __tablename__ = "vehicle_service_packages"

    id = Column(Integer, primary_key=True, index=True)
    model_id = Column(Integer, index=True, nullable=False)
    package_code = Column(String(255), index=True, nullable=True)
    package_name = Column(String(255), nullable=False)
    description = Column(String(255), nullable=True)
    recommended_interval_km = Column(Integer, nullable=True)
    recommended_interval_months = Column(Integer, nullable=True)
    labor_hours_total = Column(Float, nullable=True)
    labor_price_total = Column(Float, nullable=True)
    parts_price_total = Column(Float, nullable=True)
    suggested_price_total = Column(Float, nullable=True)
    sort_order = Column(Integer, nullable=False, default=100)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class VehicleServicePackageItem(Base):
    __tablename__ = "vehicle_service_package_items"

    id = Column(Integer, primary_key=True, index=True)
    package_id = Column(Integer, index=True, nullable=False)
    template_item_id = Column(Integer, index=True, nullable=False)
    sort_order = Column(Integer, nullable=False, default=100)
    is_optional = Column(Boolean, nullable=False, default=False)
    notes = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

