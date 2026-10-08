from dataclasses import dataclass
from datetime import datetime

from app.domain.entities._validation import optional_text, require_positive, require_text
from app.domain.entities.event import Event
from app.domain.exceptions import InvalidValueError
from app.domain.value_objects import TimeRange


@dataclass(slots=True, kw_only=True)
class Session:
    event_id: int
    title: str
    start_time: datetime
    end_time: datetime
    speaker_id: int | None = None
    description: str | None = None
    capacity: int | None = None
    id: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        self.title = require_text(self.title, "title")
        self.description = optional_text(self.description)
        if self.capacity is not None:
            self.capacity = require_positive(self.capacity, "capacity")
        TimeRange(self.start_time, self.end_time)

    @property
    def schedule(self) -> TimeRange:
        return TimeRange(self.start_time, self.end_time)

    def ensure_fits_within(self, event: Event) -> None:
        if not event.schedule.contains(self.schedule):
            raise InvalidValueError("Session must take place within the event schedule")
