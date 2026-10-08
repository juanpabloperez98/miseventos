from datetime import UTC, datetime, timedelta
from typing import Any

from app.domain.entities import Event, Session, User
from app.domain.enums import EventStatus, UserRole

EVENT_START = datetime(2030, 5, 10, 9, 0, tzinfo=UTC)


def build_user(**overrides: Any) -> User:
    values: dict[str, Any] = {
        "name": "Ada Lovelace",
        "email": "ada@example.com",
        "password_hash": "salt$digest",
        "role": UserRole.ATTENDEE,
    }
    values.update(overrides)
    return User(**values)


def build_event(**overrides: Any) -> Event:
    values: dict[str, Any] = {
        "name": "PyCon Colombia",
        "description": "Python conference",
        "location": "Medellin",
        "start_date": EVENT_START,
        "end_date": EVENT_START + timedelta(days=2),
        "capacity": 100,
        "created_by": 1,
        "status": EventStatus.PUBLISHED,
    }
    values.update(overrides)
    return Event(**values)


def build_session(**overrides: Any) -> Session:
    values: dict[str, Any] = {
        "event_id": 1,
        "title": "Hexagonal architecture in Python",
        "start_time": EVENT_START + timedelta(hours=1),
        "end_time": EVENT_START + timedelta(hours=2),
        "capacity": 30,
    }
    values.update(overrides)
    return Session(**values)
