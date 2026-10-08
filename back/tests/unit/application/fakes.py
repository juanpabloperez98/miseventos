from dataclasses import replace
from datetime import UTC, datetime

from app.domain.entities import Event, Registration, User
from app.domain.enums import EventStatus
from app.domain.exceptions import NotFoundError
from app.domain.ports import (
    EventRepository,
    EventSearchCriteria,
    EventVisibility,
    RegistrationRepository,
    UnitOfWork,
    UserRepository,
)
from app.domain.value_objects import Page, PageRequest


class InMemoryUserRepository(UserRepository):
    def __init__(self) -> None:
        self._users: dict[int, User] = {}

    def add(self, user: User) -> User:
        now = datetime.now(UTC)
        stored = replace(user, id=len(self._users) + 1, created_at=now, updated_at=now)
        self._users[stored.id or 0] = stored
        return stored

    def get_by_id(self, user_id: int) -> User | None:
        return self._users.get(user_id)

    def get_by_email(self, email: str) -> User | None:
        return next((user for user in self._users.values() if user.email == email), None)


class InMemoryEventRepository(EventRepository):
    def __init__(self) -> None:
        self._events: dict[int, Event] = {}
        self._next_id = 1

    def add(self, event: Event) -> Event:
        now = datetime.now(UTC)
        stored = replace(event, id=self._next_id, created_at=now, updated_at=now)
        self._events[self._next_id] = stored
        self._next_id += 1
        return stored

    def get_by_id(self, event_id: int) -> Event | None:
        return self._events.get(event_id)

    def get_by_id_for_update(self, event_id: int) -> Event | None:
        return self.get_by_id(event_id)

    def update(self, event: Event) -> Event:
        if event.id not in self._events:
            raise NotFoundError.for_entity("Event")
        stored = replace(event, updated_at=datetime.now(UTC))
        self._events[event.id] = stored
        return stored

    def delete(self, event_id: int) -> None:
        if self._events.pop(event_id, None) is None:
            raise NotFoundError.for_entity("Event")

    def search(self, criteria: EventSearchCriteria, page: PageRequest) -> Page[Event]:
        matches = sorted(
            (event for event in self._events.values() if self._matches(event, criteria)),
            key=lambda event: (event.start_date, event.id or 0),
        )
        items = matches[page.offset : page.offset + page.per_page]
        return Page(items=items, total=len(matches), request=page)

    def list_by_attendee(self, user_id: int) -> list[Event]:
        raise NotImplementedError

    @staticmethod
    def _matches(event: Event, criteria: EventSearchCriteria) -> bool:
        if not _is_visible(event, criteria.visibility):
            return False
        if criteria.name and criteria.name.lower() not in event.name.lower():
            return False
        return criteria.status is None or event.status is criteria.status


def _is_visible(event: Event, visibility: EventVisibility) -> bool:
    return (
        visibility.include_unpublished
        or event.status is EventStatus.PUBLISHED
        or event.created_by == visibility.owner_id
    )


class InMemoryRegistrationRepository(RegistrationRepository):
    def __init__(self) -> None:
        self._registrations: dict[int, Registration] = {}

    def add(self, registration: Registration) -> Registration:
        stored = replace(registration, id=len(self._registrations) + 1)
        self._registrations[stored.id or 0] = stored
        return stored

    def get(self, user_id: int, event_id: int) -> Registration | None:
        return next(
            (
                registration
                for registration in self._registrations.values()
                if registration.user_id == user_id and registration.event_id == event_id
            ),
            None,
        )

    def delete(self, registration_id: int) -> None:
        del self._registrations[registration_id]

    def count_by_event(self, event_id: int) -> int:
        return sum(1 for item in self._registrations.values() if item.event_id == event_id)


class SpyUnitOfWork(UnitOfWork):
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1
