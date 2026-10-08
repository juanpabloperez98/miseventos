import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any, TextIO

from app._telemetry import TELEMETRY_NAMESPACE

_STANDARD_RECORD_ATTRIBUTES = frozenset(
    vars(logging.LogRecord("", logging.INFO, "", 0, "", None, None))
) | {"message", "asctime"}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "namespace": TELEMETRY_NAMESPACE,
            "message": record.getMessage(),
        }
        payload.update(
            (key, value)
            for key, value in vars(record).items()
            if key not in _STANDARD_RECORD_ATTRIBUTES
        )
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


class _AppLogHandler(logging.StreamHandler[TextIO]):
    pass


def configure_logging(level: str) -> None:
    handler = _AppLogHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    root_logger = logging.getLogger()
    for existing in [h for h in root_logger.handlers if isinstance(h, _AppLogHandler)]:
        root_logger.removeHandler(existing)
    root_logger.addHandler(handler)
    root_logger.setLevel(level)

    logging.getLogger("werkzeug").setLevel(logging.WARNING)
