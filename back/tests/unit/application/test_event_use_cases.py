from datetime import timedelta
from typing import Any

import pytest

from app.application.dto import Actor, EventDetails, ListEventsQuery, UpdateEventCommand
from app.application.services import AuthorizationService, EventAccessPolicy
from app.application.use_cases.events import (
    CreateEventUseCase,
    DeleteEventUseCase,
    GetEventUseCase,
    ListEventsUseCase,
    UpdateEventUseCase,
)
from app.domain.entities import Event, Registration
from app.domain.enums import EventRemoval, EventStatus, UserRole
from app.domain.exceptions import (
    AuthorizationError,
    EventCannotBeRemovedError,
    EventCapacityBelowRegistrationsError,
    EventNotEditableError,
    InvalidEventStatusTransitionError,
    InvalidValueError,
    NotFoundError,
)
from tests.factories import EVENT_START, build_event
from tests.unit.application.fakes import (
    InMemoryEventRepository,
    InMemoryRegistrationRepository,
    SpyUnitOfWork,
)

OWNER = Actor(user_id=10, role=UserRole.ORGANIZER)
OTHER_ORGANIZER = Actor(user_id=20, role=UserRole.ORGANIZER)
ADMIN = Actor(user_id=1, role=UserRole.ADMIN)
ATTENDEE = Actor(user_id=30, role=UserRole.ATTENDEE)


def _details(**overrides: Any) -> EventDetails:
    values: dict[str, Any] = {
        "name": "Python Conference",
        "description": "Talks and workshops",
        "location": "Bogota",
        "start_date": EVENT_START,
        "end_date": EVENT_START + timedelta(hours=8),
        "capacity": 100,
    }
    values.update(overrides)
    return EventDetails(**values)


@pytest.fixture
def events() -> InMemoryEventRepository:
    return InMemoryEventRepository()


@pytest.fixture
def registrations() -> InMemoryRegistrationRepository:
    return InMemoryRegistrationRepository()


@pytest.fixture
def unit_of_work() -> SpyUnitOfWork:
    return SpyUnitOfWork()


@pytest.fixture
def policy() -> EventAccessPolicy:
    return EventAccessPolicy(AuthorizationService())


@pytest.fixture
def owned_event(events: InMemoryEventRepository) -> Event:
    return events.add(build_event(created_by=OWNER.user_id, status=EventStatus.DRAFT))


class TestCreateEvent:
    @pytest.fixture
    def create(
        self,
        events: InMemoryEventRepository,
        policy: EventAccessPolicy,
        unit_of_work: SpyUnitOfWork,
    ) -> CreateEventUseCase:
        return CreateEventUseCase(events, policy, unit_of_work)

    @pytest.mark.parametrize("actor", [OWNER, ADMIN])
    def test_creates_draft_owned_by_the_actor(
        self,
        create: CreateEventUseCase,
        events: InMemoryEventRepository,
        unit_of_work: SpyUnitOfWork,
        actor: Actor,
    ) -> None:
        event = create.execute(actor, _details())

        assert event.id is not None
        assert events.get_by_id(event.id) == event
        assert event.status is EventStatus.DRAFT
        assert event.created_by == actor.user_id
        assert unit_of_work.commits == 1

    def test_attendees_cannot_create_events(
        self, create: CreateEventUseCase, unit_of_work: SpyUnitOfWork
    ) -> None:
        with pytest.raises(AuthorizationError):
            create.execute(ATTENDEE, _details())
        assert unit_of_work.commits == 0

    @pytest.mark.parametrize(
        "overrides",
        [{"capacity": 0}, {"name": " "}, {"end_date": EVENT_START - timedelta(minutes=1)}],
    )
    def test_rejects_invalid_details(
        self, create: CreateEventUseCase, overrides: dict[str, Any]
    ) -> None:
        with pytest.raises(InvalidValueError):
            create.execute(OWNER, _details(**overrides))


class TestGetEvent:
    @pytest.fixture
    def get_event(
        self, events: InMemoryEventRepository, policy: EventAccessPolicy
    ) -> GetEventUseCase:
        return GetEventUseCase(events, policy)

    def test_published_events_are_public(
        self, get_event: GetEventUseCase, events: InMemoryEventRepository
    ) -> None:
        event = events.add(build_event(status=EventStatus.PUBLISHED))

        assert get_event.execute(event.id or 0) == event

    @pytest.mark.parametrize("actor", [None, ATTENDEE, OTHER_ORGANIZER])
    def test_hides_unpublished_events_from_non_managers(
        self, get_event: GetEventUseCase, owned_event: Event, actor: Actor | None
    ) -> None:
        with pytest.raises(NotFoundError, match="Event not found"):
            get_event.execute(owned_event.id or 0, actor)

    @pytest.mark.parametrize("actor", [OWNER, ADMIN])
    def test_managers_see_unpublished_events(
        self, get_event: GetEventUseCase, owned_event: Event, actor: Actor
    ) -> None:
        assert get_event.execute(owned_event.id or 0, actor) == owned_event

    def test_missing_event(self, get_event: GetEventUseCase) -> None:
        with pytest.raises(NotFoundError):
            get_event.execute(999, ADMIN)


class TestListEvents:
    @pytest.fixture
    def list_events(
        self, events: InMemoryEventRepository, policy: EventAccessPolicy
    ) -> ListEventsUseCase:
        for day, (name, owner, status) in enumerate(
            [
                ("Python Conference", OTHER_ORGANIZER, EventStatus.PUBLISHED),
                ("Advanced python", OTHER_ORGANIZER, EventStatus.PUBLISHED),
                ("Rust Meetup", OTHER_ORGANIZER, EventStatus.PUBLISHED),
                ("My Python draft", OWNER, EventStatus.DRAFT),
                ("Foreign draft", OTHER_ORGANIZER, EventStatus.DRAFT),
            ]
        ):
            events.add(
                build_event(
                    name=name,
                    created_by=owner.user_id,
                    status=status,
                    start_date=EVENT_START + timedelta(days=day),
                    end_date=EVENT_START + timedelta(days=day, hours=2),
                )
            )
        return ListEventsUseCase(events, policy)

    @staticmethod
    def _names(list_events: ListEventsUseCase, actor: Actor | None, **query: Any) -> list[str]:
        return [event.name for event in list_events.execute(ListEventsQuery(**query), actor).items]

    @pytest.mark.parametrize(
        ("actor", "expected"),
        [
            (None, ["Python Conference", "Advanced python", "Rust Meetup"]),
            (ATTENDEE, ["Python Conference", "Advanced python", "Rust Meetup"]),
            (OWNER, ["Python Conference", "Advanced python", "Rust Meetup", "My Python draft"]),
            (
                ADMIN,
                [
                    "Python Conference",
                    "Advanced python",
                    "Rust Meetup",
                    "My Python draft",
                    "Foreign draft",
                ],
            ),
        ],
    )
    def test_visibility_depends_on_actor(
        self, list_events: ListEventsUseCase, actor: Actor | None, expected: list[str]
    ) -> None:
        assert self._names(list_events, actor) == expected

    @pytest.mark.parametrize("search", ["python", "PYTHON", "  Python  "])
    def test_search_by_name_is_case_insensitive_and_trimmed(
        self, list_events: ListEventsUseCase, search: str
    ) -> None:
        assert self._names(list_events, None, search=search) == [
            "Python Conference",
            "Advanced python",
        ]

    def test_blank_search_returns_everything_visible(self, list_events: ListEventsUseCase) -> None:
        assert len(self._names(list_events, None, search="   ")) == 3

    def test_status_filter_respects_visibility(self, list_events: ListEventsUseCase) -> None:
        assert self._names(list_events, None, status=EventStatus.DRAFT) == []
        assert self._names(list_events, OWNER, status=EventStatus.DRAFT) == ["My Python draft"]

    def test_paginates(self, list_events: ListEventsUseCase) -> None:
        page = list_events.execute(ListEventsQuery(page=2, per_page=2))

        assert [event.name for event in page.items] == ["Rust Meetup"]
        assert (page.total, page.pages) == (3, 2)

    def test_rejects_invalid_pagination(self, list_events: ListEventsUseCase) -> None:
        with pytest.raises(InvalidValueError):
            list_events.execute(ListEventsQuery(per_page=1000))


class TestUpdateEvent:
    @pytest.fixture
    def update(
        self,
        events: InMemoryEventRepository,
        registrations: InMemoryRegistrationRepository,
        policy: EventAccessPolicy,
        unit_of_work: SpyUnitOfWork,
    ) -> UpdateEventUseCase:
        return UpdateEventUseCase(events, registrations, policy, unit_of_work)

    @pytest.mark.parametrize("actor", [OWNER, ADMIN])
    def test_owner_and_admin_can_update(
        self,
        update: UpdateEventUseCase,
        owned_event: Event,
        unit_of_work: SpyUnitOfWork,
        actor: Actor,
    ) -> None:
        command = UpdateEventCommand(
            event_id=owned_event.id or 0,
            details=_details(name="Renamed", capacity=40),
            status=EventStatus.PUBLISHED,
        )

        updated = update.execute(actor, command)

        assert (updated.name, updated.capacity, updated.status) == (
            "Renamed",
            40,
            EventStatus.PUBLISHED,
        )
        assert updated.created_by == OWNER.user_id
        assert unit_of_work.commits == 1

    def test_omitted_status_keeps_the_current_one(
        self, update: UpdateEventUseCase, owned_event: Event
    ) -> None:
        updated = update.execute(OWNER, UpdateEventCommand(owned_event.id or 0, _details()))

        assert updated.status is EventStatus.DRAFT

    @pytest.mark.parametrize("actor", [OTHER_ORGANIZER, ATTENDEE])
    def test_non_owners_cannot_update(
        self,
        update: UpdateEventUseCase,
        owned_event: Event,
        unit_of_work: SpyUnitOfWork,
        actor: Actor,
    ) -> None:
        with pytest.raises(AuthorizationError):
            update.execute(actor, UpdateEventCommand(owned_event.id or 0, _details()))
        assert unit_of_work.commits == 0

    def test_attendee_gets_forbidden_even_for_missing_events(
        self, update: UpdateEventUseCase
    ) -> None:
        with pytest.raises(AuthorizationError):
            update.execute(ATTENDEE, UpdateEventCommand(999, _details()))

    def test_missing_event(self, update: UpdateEventUseCase) -> None:
        with pytest.raises(NotFoundError):
            update.execute(ADMIN, UpdateEventCommand(999, _details()))

    def test_rejects_invalid_transition(
        self, update: UpdateEventUseCase, owned_event: Event
    ) -> None:
        command = UpdateEventCommand(owned_event.id or 0, _details(), EventStatus.COMPLETED)

        with pytest.raises(InvalidEventStatusTransitionError):
            update.execute(OWNER, command)

    def test_rejects_editing_final_events(
        self, update: UpdateEventUseCase, events: InMemoryEventRepository
    ) -> None:
        cancelled = events.add(build_event(created_by=OWNER.user_id, status=EventStatus.CANCELLED))

        with pytest.raises(EventNotEditableError):
            update.execute(OWNER, UpdateEventCommand(cancelled.id or 0, _details()))

    def test_capacity_cannot_drop_below_registrations(
        self,
        update: UpdateEventUseCase,
        events: InMemoryEventRepository,
        registrations: InMemoryRegistrationRepository,
    ) -> None:
        event = events.add(build_event(created_by=OWNER.user_id, capacity=10))
        for user_id in range(3):
            registrations.add(Registration(user_id=user_id, event_id=event.id or 0))

        with pytest.raises(EventCapacityBelowRegistrationsError):
            update.execute(OWNER, UpdateEventCommand(event.id or 0, _details(capacity=2)))


class TestDeleteEvent:
    @pytest.fixture
    def delete(
        self,
        events: InMemoryEventRepository,
        policy: EventAccessPolicy,
        unit_of_work: SpyUnitOfWork,
    ) -> DeleteEventUseCase:
        return DeleteEventUseCase(events, policy, unit_of_work)

    def test_draft_events_are_deleted(
        self,
        delete: DeleteEventUseCase,
        events: InMemoryEventRepository,
        owned_event: Event,
        unit_of_work: SpyUnitOfWork,
    ) -> None:
        result = delete.execute(OWNER, owned_event.id or 0)

        assert result.action is EventRemoval.DELETE
        assert result.event is None
        assert events.get_by_id(owned_event.id or 0) is None
        assert unit_of_work.commits == 1

    def test_published_events_are_cancelled(
        self, delete: DeleteEventUseCase, events: InMemoryEventRepository
    ) -> None:
        published = events.add(build_event(created_by=OWNER.user_id))

        result = delete.execute(ADMIN, published.id or 0)

        assert result.action is EventRemoval.CANCEL
        assert result.event is not None
        assert result.event.status is EventStatus.CANCELLED
        assert events.get_by_id(published.id or 0) == result.event

    @pytest.mark.parametrize("status", [EventStatus.CANCELLED, EventStatus.COMPLETED])
    def test_final_events_cannot_be_removed(
        self,
        delete: DeleteEventUseCase,
        events: InMemoryEventRepository,
        unit_of_work: SpyUnitOfWork,
        status: EventStatus,
    ) -> None:
        event = events.add(build_event(created_by=OWNER.user_id, status=status))

        with pytest.raises(EventCannotBeRemovedError):
            delete.execute(OWNER, event.id or 0)
        assert unit_of_work.commits == 0

    @pytest.mark.parametrize("actor", [OTHER_ORGANIZER, ATTENDEE])
    def test_non_owners_cannot_delete(
        self,
        delete: DeleteEventUseCase,
        events: InMemoryEventRepository,
        owned_event: Event,
        actor: Actor,
    ) -> None:
        with pytest.raises(AuthorizationError):
            delete.execute(actor, owned_event.id or 0)
        assert events.get_by_id(owned_event.id or 0) == owned_event

    def test_missing_event(self, delete: DeleteEventUseCase) -> None:
        with pytest.raises(NotFoundError):
            delete.execute(ADMIN, 999)
