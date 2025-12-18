from sqlalchemy.orm import Session
from ..models import AuditLog
import json

def log_audit(db: Session, actor_id: str, action: str, target: str, before: dict = None, after: dict = None):
    try:
        log = AuditLog(
            actor_id=actor_id,
            action=action,
            target_entity=target,
            before_state=before,
            after_state=after
        )
        db.add(log)
        db.commit()
    except Exception as e:
        print(f"Audit log failed: {e}")
