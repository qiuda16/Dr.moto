from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
import json
import logging

from ..core.db import get_db
from ..models import EventLog
from ..schemas.event import EventIngest, EventResponse
from ..integrations.mq import event_bus

router = APIRouter(prefix="/events", tags=["Edge Events"])
logger = logging.getLogger("bff")

@router.post("/ingest", response_model=EventResponse)
async def ingest_event(
    event: EventIngest, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    try:
        # 1. Log to DB
        db_event = EventLog(
            event_id=event.event_id,
            event_type=event.event_type,
            source=event.source,
            payload=json.dumps(event.payload)
        )
        db.add(db_event)
        db.commit()
        
        # 2. Publish to internal bus (RabbitMQ/Redis)
        # This allows other services (like AI or Odoo Sync) to react
        event_bus.publish(f"edge:{event.event_type}", event.dict())
        
        # 3. Simple Rule Engine (MVP Gate)
        if event.event_type == "rule_violation":
            background_tasks.add_task(trigger_voice_alert, event.payload.get("description", "Safety Violation"))
            
        return {"status": "received", "processed": True}
        
    except Exception as e:
        logger.error(f"Failed to ingest event: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=list)
async def get_recent_events(limit: int = 10, db: Session = Depends(get_db)):
    events = db.query(EventLog).order_by(EventLog.created_at.desc()).limit(limit).all()
    return [
        {
            "id": e.event_id,
            "type": e.event_type,
            "source": e.source,
            "payload": json.loads(e.payload),
            "timestamp": e.created_at
        }
        for e in events
    ]

async def trigger_voice_alert(message: str):
    # In a real system, this would push back to the Edge Voice module via MQTT or WebSocket
    # For MVP, we'll just log it heavily
    logger.warning(f"!!! VOICE ALERT TRIGGERED !!! Saying: {message}")
