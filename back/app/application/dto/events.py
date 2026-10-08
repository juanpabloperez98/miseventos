from dataclasses import dataclass
from datetime import datetime

from app.domain.entities import Event
from app.domain.enums import EventRemoval, EventStatus


@dataclass(frozen=True, slots=True)
class ListEventsQuery:
    search: str | None = None
    status: EventStatus | None = None
    page: int = 1
    per_page: int = 10


@dataclass(frozen=True, slots=True)
class EventDetails:
    name: str
    location: str
    start_date: datetime
    end_date: datetime
    capacity: int
    description: str | None = None


@dataclass(frozen=True, slots=True)
class UpdateEventCommand:
    event_id: int
    details: EventDetails
    status: EventStatus | None = None


@dataclass(frozen=True, slots=True)
class EventRemovalResult:
    action: EventRemoval
    event: Event | None = None
