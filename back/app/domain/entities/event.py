from dataclasses import dataclass, replace
from datetime import datetime

from app.domain.entities._validation import optional_text, require_positive, require_text
from app.domain.entities.event_image import EventImage
from app.domain.enums import EventRemoval, EventStatus
from app.domain.exceptions import (
    EventCannotBeRemovedError,
    EventCapacityBelowRegistrationsError,
    EventCapacityExceededError,
    EventNotEditableError,
    EventNotOpenForRegistrationError,
    InvalidEventStatusTransitionError,
)
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
    # Read only: loaded with the event, changed through the event image use cases.
    image: EventImage | None = None
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
    def is_publicly_visible(self) -> bool:
        return self.status is EventStatus.PUBLISHED

    @property
    def is_open_for_registration(self) -> bool:
        return self.status is EventStatus.PUBLISHED

    def is_owned_by(self, user_id: int) -> bool:
        return self.created_by == user_id

    def ensure_editable(self) -> None:
        if self.status.is_final:
            raise EventNotEditableError()

    def ensure_can_accept_registration(self, registered_count: int) -> None:
        if not self.is_open_for_registration:
            raise EventNotOpenForRegistrationError()
        if registered_count >= self.capacity:
            raise EventCapacityExceededError()

    def with_details(
        self,
        *,
        name: str,
        description: str | None,
        location: str,
        start_date: datetime,
        end_date: datetime,
        capacity: int,
        registered_count: int,
    ) -> "Event":
        self.ensure_editable()
        updated = replace(
            self,
            name=name,
            description=description,
            location=location,
            start_date=start_date,
            end_date=end_date,
            capacity=capacity,
        )
        if updated.capacity < registered_count:
            raise EventCapacityBelowRegistrationsError()
        return updated

    def with_status(self, status: EventStatus) -> "Event":
        if status is self.status:
            return self
        if not self.status.can_transition_to(status):
            raise InvalidEventStatusTransitionError(
                f"Cannot change event status from {self.status.value} to {status.value}"
            )
        return replace(self, status=status)

    def removal_action(self) -> EventRemoval:
        if self.status is EventStatus.DRAFT:
            return EventRemoval.DELETE
        if self.status is EventStatus.PUBLISHED:
            return EventRemoval.CANCEL
        raise EventCannotBeRemovedError(f"{self.status.value} events cannot be removed")
