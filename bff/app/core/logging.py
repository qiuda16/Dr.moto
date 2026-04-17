import json
import logging
from datetime import datetime, timezone

from .config import settings


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key in ("trace_id", "method", "path", "status_code", "process_time_ms"):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def setup_logging() -> None:
    level_name = settings.LOG_LEVEL.upper()
    level = getattr(logging, level_name, logging.INFO)
    root = logging.getLogger()
    root.setLevel(level)

    handler = logging.StreamHandler()
    if settings.LOG_FORMAT.strip().lower() == "plain":
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)s %(name)s [trace=%(trace_id)s] %(message)s",
                defaults={"trace_id": "-"},
            )
        )
    else:
        handler.setFormatter(JsonFormatter())

    root.handlers = [handler]
