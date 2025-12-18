from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.sql import func
from .core.db import Base

class PaymentLedger(Base):
    __tablename__ = "payment_ledger"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(String, unique=True, index=True, nullable=False)
    work_order_id = Column(String, index=True, nullable=False)
    amount = Column(Float, nullable=False)
    status = Column(String, default="pending")
    provider = Column(String, default="wechat")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class WorkOrderAttachment(Base):
    __tablename__ = "work_order_attachments"

    id = Column(Integer, primary_key=True, index=True)
    work_order_uuid = Column(String, index=True, nullable=False)
    file_name = Column(String, nullable=False)
    file_url = Column(String, nullable=False)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())

class EventLog(Base):
    __tablename__ = "event_logs"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String, unique=True, index=True)
    event_type = Column(String, index=True) # tool_detected, rule_violation, etc.
    source = Column(String) # cv, voice, iot
    payload = Column(String) # JSON string
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class WorkOrder(Base):
    __tablename__ = "work_orders"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String, unique=True, index=True, nullable=False) # Internal BFF ID
    odoo_id = Column(Integer, nullable=True) # ID in Odoo (Repair Order ID)
    customer_id = Column(String, nullable=False)
    vehicle_plate = Column(String, nullable=False)
    vehicle_key = Column(String, nullable=True) # e.g., TOYOTA|COROLLA|2020|1.8
    description = Column(String, nullable=True)
    status = Column(String, default="draft")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Vehicle(Base):
    __tablename__ = "vehicles"
    
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True, nullable=False) # make|model|year|engine
    make = Column(String, nullable=False)
    model = Column(String, nullable=False)
    year_from = Column(Integer, nullable=False)
    year_to = Column(Integer, nullable=True)
    engine_code = Column(String, nullable=True)
    
class Procedure(Base):
    __tablename__ = "procedures"
    
    id = Column(Integer, primary_key=True, index=True)
    vehicle_key = Column(String, index=True, nullable=False) # FK to Vehicle.key (loose coupling)
    name = Column(String, nullable=False) # e.g. "Oil Change"
    description = Column(String)
    
class ProcedureStep(Base):
    __tablename__ = "procedure_steps"
    
    id = Column(Integer, primary_key=True, index=True)
    procedure_id = Column(Integer, nullable=False, index=True)
    step_order = Column(Integer, nullable=False)
    instruction = Column(String, nullable=False)
    required_tools = Column(String) # JSON list of tool IDs
    torque_spec = Column(String) # JSON: {value: 120, unit: "Nm"}
    hazards = Column(String) # JSON list
