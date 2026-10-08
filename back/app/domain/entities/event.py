from dataclasses import dataclass
from datetime import datetime

from app.domain.entities._validation import optional_text, require_positive, require_text
from app.domain.enums import EventStatus
from app.domain.exceptions import EventCapacityExceededError, EventNotOpenForRegistrationError
from app.domain.value_objects import TimeRange


@dataclass(slots=True, kw_only=True)
class Event:
    name: str
    location: str
    start_date: datetime
    end_date: datetime
    capacity: int
    created_by: int
    description: str | None = None
    status: EventStatus = EventStatus.DRAFT
    id: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        self.name = require_text(self.name, "name")
        self.location = require_text(self.location, "location")
        self.description = optional_text(self.description)
        self.capacity = require_positive(self.capacity, "capacity")
        TimeRange(self.start_date, self.end_date)

    @property
    def schedule(self) -> TimeRange:
        return TimeRange(self.start_date, self.end_date)

    @property
    def is_open_for_registration(self) -> bool:
        return self.status is EventStatus.PUBLISHED

    def ensure_can_accept_registration(self, registered_count: int) -> None:
        if not self.is_open_for_registration:
            raise EventNotOpenForRegistrationError()
        if registered_count >= self.capacity:
            raise EventCapacityExceededError()
