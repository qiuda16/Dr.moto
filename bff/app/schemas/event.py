from pydantic import BaseModel
from typing import Dict, Any, Optional
from datetime import datetime

class EventIngest(BaseModel):
    event_id: str
    timestamp: datetime
    event_type: str  # tool_detected, hand_action, rule_violation, voice_command, etc.
    source: str      # cv, voice, iot_gateway
    payload: Dict[str, Any]

class EventResponse(BaseModel):
    status: str
    processed: bool
