from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.domain.entities import Event
from app.domain.enums import EventStatus
from app.domain.value_objects import Page, PageRequest


@dataclass(frozen=True, slots=True)
class EventVisibility:
    include_unpublished: bool = False
    owner_id: int | None = None

    @classmethod
    def public(cls) -> "EventVisibility":
        return cls()

    @classmethod
    def unrestricted(cls) -> "EventVisibility":
        return cls(include_unpublished=True)

    @classmethod
    def public_or_owned_by(cls, owner_id: int) -> "EventVisibility":
        return cls(owner_id=owner_id)


@dataclass(frozen=True, slots=True)
class EventSearchCriteria:
    visibility: EventVisibility
    name: str | None = None
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
