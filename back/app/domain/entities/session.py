from dataclasses import dataclass, replace
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
    capacity: int
    speaker_id: int | None = None
    description: str | None = None
    id: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        self.title = require_text(self.title, "title")
        self.description = optional_text(self.description)
        self.capacity = require_positive(self.capacity, "capacity")
        TimeRange(self.start_time, self.end_time)

    @property
    def schedule(self) -> TimeRange:
        return TimeRange(self.start_time, self.end_time)

    def ensure_fits_within(self, event: Event) -> None:
        if not event.schedule.contains(self.schedule):
            raise InvalidValueError("Session must take place within the event schedule")

    def with_details(
        self,
        *,
        title: str,
        description: str | None,
        start_time: datetime,
        end_time: datetime,
        capacity: int,
        speaker_id: int | None,
    ) -> "Session":
        return replace(
            self,
            title=title,
            description=description,
            start_time=start_time,
            end_time=end_time,
            capacity=capacity,
            speaker_id=speaker_id,
        )
