from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.domain.entities import Event
from app.domain.enums import EventStatus
from app.domain.value_objects import Page, PageRequest


@dataclass(frozen=True, slots=True)
class EventSearchCriteria:
    text: str | None = None
    status: EventStatus | None = None


class EventRepository(ABC):
    @abstractmethod
    def add(self, event: Event) -> Event: ...

    @abstractmethod
    def get_by_id(self, event_id: int) -> Event | None: ...

    @abstractmethod
    def get_by_id_for_update(self, event_id: int) -> Event | None:
        """Load the event holding a row-level lock until the current transaction ends."""

    @abstractmethod
    def update(self, event: Event) -> Event: ...

    @abstractmethod
    def delete(self, event_id: int) -> None: ...

    @abstractmethod
    def search(self, criteria: EventSearchCriteria, page: PageRequest) -> Page[Event]: ...

    @abstractmethod
    def list_by_attendee(self, user_id: int) -> list[Event]: ...
