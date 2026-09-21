import json
import logging
from contextvars import ContextVar
from datetime import UTC, datetime

from app.core.config import Settings

request_id_context: ContextVar[str | None] = ContextVar("request_id", default=None)
actor_context: ContextVar[str | None] = ContextVar("actor", default=None)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "service": getattr(record, "service", "ai-soc-backend"),
            "request_id": getattr(record, "request_id", None) or request_id_context.get(),
            "actor": getattr(record, "actor", None) or actor_context.get(),
            "event": getattr(record, "event", record.name),
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload)


def configure_logging(settings: Settings) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(settings.log_level.upper())
