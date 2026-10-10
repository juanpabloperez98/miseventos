import json
import logging

from app._telemetry import TELEMETRY_NAMESPACE
from app.infrastructure.logging_config import JsonFormatter


def test_telemetry_namespace_is_the_required_value() -> None:
    assert TELEMETRY_NAMESPACE == "miseventos.events.v1"


def test_json_log_records_carry_the_telemetry_namespace() -> None:
    record = logging.LogRecord("app.test", logging.INFO, __file__, 1, "event_created", None, None)
    record.event_id = 7

    payload = json.loads(JsonFormatter().format(record))

    assert payload["namespace"] == "miseventos.events.v1"
    assert payload["message"] == "event_created"
    assert payload["event_id"] == 7
