import queue
import threading
import time
import logging
from typing import Callable, Dict

logger = logging.getLogger("event_bus")

class EventBus:
    def __init__(self):
        self.subscribers: Dict[str, list[Callable]] = {}
        self.queue = queue.Queue()
        self.worker_thread = threading.Thread(target=self._worker, daemon=True)
        self.worker_thread.start()

    def subscribe(self, event_type: str, handler: Callable):
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(handler)

    def publish(self, event_type: str, payload: dict):
        """Async publish to queue."""
        self.queue.put((event_type, payload))

    def _worker(self):
        while True:
            try:
                event_type, payload = self.queue.get()
                handlers = self.subscribers.get(event_type, [])
                for handler in handlers:
                    try:
                        handler(payload)
                    except Exception as e:
                        logger.error(f"Error handling event {event_type}: {e}")
                self.queue.task_done()
            except Exception as e:
                logger.error(f"Event bus worker error: {e}")

# Global instance
event_bus = EventBus()

# --- Example Handlers ---
def log_event_to_db(payload):
    # In a real app, this would write to the EventLog table
    logger.info(f"AUDIT: Event received -> {payload}")

event_bus.subscribe("evt:work_order_updated", log_event_to_db)
event_bus.subscribe("evt:media_uploaded", log_event_to_db)
