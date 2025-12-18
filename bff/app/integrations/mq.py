import json
import redis
from ..core.config import settings

class EventBus:
    def __init__(self):
        self.client = redis.Redis.from_url(settings.REDIS_URL)
    
    def publish(self, stream: str, payload: dict):
        data = {k: json.dumps(v) if isinstance(v, (dict, list)) else str(v) for k, v in payload.items()}
        self.client.xadd(stream, data, maxlen=1000, approximate=True)

event_bus = EventBus()
