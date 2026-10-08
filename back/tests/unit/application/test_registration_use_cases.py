from datetime import timedelta

import pytest

from app.application.dto import Actor
from app.application.services import AuthorizationService, EventAccessPolicy
from app.application.use_cases.registrations import (
    ListMyRegisteredEventsUseCase,
    RegisterForEventUseCase,
)
from app.domain.entities import Event, Registration
from app.domain.enums import EventStatus, UserRole
from app.domain.exceptions import (
    AlreadyRegisteredToEventError,
    EventCapacityExceededError,
    EventNotOpenForRegistrationError,
    NotFoundError,
)
from tests.factories import EVENT_START, build_event
from tests.unit.application.fakes import (
    InMemoryEventRepository,
    InMemoryRegistrationRepository,
    SpyUnitOfWork,
)

OWNER = Actor(user_id=10, role=UserRole.ORGANIZER)
ADMIN = Actor(user_id=1, role=UserRole.ADMIN)
ATTENDEE = Actor(user_id=30, role=UserRole.ATTENDEE)
OTHER_ATTENDEE = Actor(user_id=31, role=UserRole.ATTENDEE)


@pytest.fixture
def registrations() -> InMemoryRegistrationRepository:
    return InMemoryRegistrationRepository()


@pytest.fixture
def events(registrations: InMemoryRegistrationRepository) -> InMemoryEventRepository:
    return InMemoryEventRepository(registrations)


@pytest.fixture
def unit_of_work() -> SpyUnitOfWork:
    return SpyUnitOfWork()


@pytest.fixture
def register(
    events: InMemoryEventRepository,
    registrations: InMemoryRegistrationRepository,
    unit_of_work: SpyUnitOfWork,
) -> RegisterForEventUseCase:
    authorization = AuthorizationService()
    return RegisterForEventUseCase(
        events, registrations, authorization, EventAccessPolicy(authorization), unit_of_work
    )


def _published(events: InMemoryEventRepository, capacity: int = 10, **overrides: object) -> Event:
    return events.add(build_event(created_by=OWNER.user_id, capacity=capacity, **overrides))


def _fill(registrations: InMemoryRegistrationRepository, event: Event, seats: int) -> None:
    for user_id in range(1000, 1000 + seats):
        registrations.add(Registration(user_id=user_id, event_id=event.id or 0))


class TestRegisterForEvent:
    @pytest.mark.parametrize("actor", [ATTENDEE, OWNER, ADMIN])
    def test_registers_the_actor_and_commits(
        self,
        register: RegisterForEventUseCase,
        events: InMemoryEventRepository,
        registrations: InMemoryRegistrationRepository,
        unit_of_work: SpyUnitOfWork,
        actor: Actor,
    ) -> None:
        event = _published(events)

        registration = register.execute(actor, event.id or 0)

        assert (registration.user_id, registration.event_id) == (actor.user_id, event.id)
        assert registration.id is not None
        assert registrations.get(actor.user_id, event.id or 0) == registration
        assert unit_of_work.commits == 1

    def test_last_free_seat_can_be_taken(
        self,
        register: RegisterForEventUseCase,
        events: InMemoryEventRepository,
        registrations: InMemoryRegistrationRepository,
    ) -> None:
        event = _published(events, capacity=3)
        _fill(registrations, event, 2)

        register.execute(ATTENDEE, event.id or 0)

        assert registrations.count_by_event(event.id or 0) == 3

    def test_full_event_rejects_registration(
        self,
        register: RegisterForEventUseCase,
        events: InMemoryEventRepository,
        registrations: InMemoryRegistrationRepository,
        unit_of_work: SpyUnitOfWork,
    ) -> None:
        event = _published(events, capacity=3)
        _fill(registrations, event, 3)

        with pytest.raises(EventCapacityExceededError):
            register.execute(ATTENDEE, event.id or 0)
        assert registrations.count_by_event(event.id or 0) == 3
        assert unit_of_work.commits == 0

    def test_duplicate_registration_is_rejected(
        self,
        register: RegisterForEventUseCase,
        events: InMemoryEventRepository,
        registrations: InMemoryRegistrationRepository,
        unit_of_work: SpyUnitOfWork,
    ) -> None:
        event = _published(events)
        register.execute(ATTENDEE, event.id or 0)

        with pytest.raises(AlreadyRegisteredToEventError):
            register.execute(ATTENDEE, event.id or 0)
        assert registrations.count_by_event(event.id or 0) == 1
        assert unit_of_work.commits == 1

    def test_already_registered_user_of_a_full_event_gets_duplicate_error(
        self,
        register: RegisterForEventUseCase,
        events: InMemoryEventRepository,
    ) -> None:
        event = _published(events, capacity=1)
        register.execute(ATTENDEE, event.id or 0)

        with pytest.raises(AlreadyRegisteredToEventError):
            register.execute(ATTENDEE, event.id or 0)

    def test_unknown_event(self, register: RegisterForEventUseCase) -> None:
        with pytest.raises(NotFoundError, match="Event not found"):
            register.execute(ATTENDEE, 999)

    @pytest.mark.parametrize(
        "status", [EventStatus.DRAFT, EventStatus.CANCELLED, EventStatus.COMPLETED]
    )
    def test_events_hidden_from_the_actor_are_not_found(
        self,
        register: RegisterForEventUseCase,
        events: InMemoryEventRepository,
        unit_of_work: SpyUnitOfWork,
        status: EventStatus,
    ) -> None:
        event = _published(events, status=status)

        with pytest.raises(NotFoundError, match="Event not found"):
            register.execute(ATTENDEE, event.id or 0)
        assert unit_of_work.commits == 0

    @pytest.mark.parametrize("actor", [OWNER, ADMIN])
    @pytest.mark.parametrize(
        "status", [EventStatus.DRAFT, EventStatus.CANCELLED, EventStatus.COMPLETED]
    )
    def test_visible_events_not_open_for_registration_conflict(
        self,
        register: RegisterForEventUseCase,
        events: InMemoryEventRepository,
        actor: Actor,
        status: EventStatus,
    ) -> None:
        event = _published(events, status=status)

        with pytest.raises(EventNotOpenForRegistrationError):
            register.execute(actor, event.id or 0)


class LockRecordingEventRepository(InMemoryEventRepository):
    def __init__(self) -> None:
        super().__init__()
        self.reads: list[str] = []

    def get_by_id(self, event_id: int) -> Event | None:
        self.reads.append("get_by_id")
        return super().get_by_id(event_id)

    def get_by_id_for_update(self, event_id: int) -> Event | None:
        self.reads.append("get_by_id_for_update")
        return super().get_by_id(event_id)


def test_event_is_read_with_a_row_lock(
    registrations: InMemoryRegistrationRepository, unit_of_work: SpyUnitOfWork
) -> None:
    events = LockRecordingEventRepository()
    event = _published(events)
    authorization = AuthorizationService()
    register = RegisterForEventUseCase(
        events, registrations, authorization, EventAccessPolicy(authorization), unit_of_work
    )

    register.execute(ATTENDEE, event.id or 0)

    assert events.reads == ["get_by_id_for_update"]


class TestListMyRegisteredEvents:
    @pytest.fixture
    def list_mine(self, events: InMemoryEventRepository) -> ListMyRegisteredEventsUseCase:
        return ListMyRegisteredEventsUseCase(events)

    def test_lists_only_the_actor_events_ordered_by_start(
        self,
        list_mine: ListMyRegisteredEventsUseCase,
        register: RegisterForEventUseCase,
        events: InMemoryEventRepository,
    ) -> None:
        later = _published(
            events,
            name="Later",
            start_date=EVENT_START + timedelta(days=5),
            end_date=EVENT_START + timedelta(days=6),
        )
        sooner = _published(events, name="Sooner")
        not_mine = _published(events, name="Not mine")
        register.execute(ATTENDEE, later.id or 0)
        register.execute(ATTENDEE, sooner.id or 0)
        register.execute(OTHER_ATTENDEE, not_mine.id or 0)

        assert list_mine.execute(ATTENDEE) == [sooner, later]
        assert list_mine.execute(OTHER_ATTENDEE) == [not_mine]

    def test_user_without_registrations_gets_empty_list(
        self, list_mine: ListMyRegisteredEventsUseCase, events: InMemoryEventRepository
    ) -> None:
        _published(events)

        assert list_mine.execute(ATTENDEE) == []

    def test_history_keeps_events_that_were_later_cancelled(
        self,
        list_mine: ListMyRegisteredEventsUseCase,
        register: RegisterForEventUseCase,
        events: InMemoryEventRepository,
    ) -> None:
        event = _published(events)
        register.execute(ATTENDEE, event.id or 0)
        cancelled = events.update(event.with_status(EventStatus.CANCELLED))

        assert list_mine.execute(ATTENDEE) == [cancelled]
