from datetime import datetime, timedelta
from typing import Any

import pytest

from app.application.dto import (
    Actor,
    CreateSessionCommand,
    SessionDetails,
    SessionView,
    UpdateSessionCommand,
)
from app.application.services import AuthorizationService, EventAccessPolicy
from app.application.use_cases.events import GetEventUseCase
from app.application.use_cases.sessions import (
    CreateSessionUseCase,
    DeleteSessionUseCase,
    GetSessionUseCase,
    ListEventSessionsUseCase,
    UpdateSessionUseCase,
)
from app.domain.entities import Event, Session, Speaker
from app.domain.enums import EventStatus, UserRole
from app.domain.exceptions import (
    AuthorizationError,
    EventNotEditableError,
    InvalidValueError,
    NotFoundError,
)
from tests.factories import EVENT_START, build_event, build_session
from tests.unit.application.fakes import (
    InMemoryEventRepository,
    InMemorySessionRepository,
    InMemorySpeakerRepository,
    SpyUnitOfWork,
)

OWNER = Actor(user_id=10, role=UserRole.ORGANIZER)
OTHER_ORGANIZER = Actor(user_id=20, role=UserRole.ORGANIZER)
ADMIN = Actor(user_id=1, role=UserRole.ADMIN)
ATTENDEE = Actor(user_id=30, role=UserRole.ATTENDEE)


def _at(hours: float) -> datetime:
    return EVENT_START + timedelta(hours=hours)


def _details(**overrides: Any) -> SessionDetails:
    values: dict[str, Any] = {
        "title": "Clean architecture",
        "description": "Ports and adapters",
        "start_time": _at(1),
        "end_time": _at(2),
        "capacity": 40,
        "speaker_id": None,
    }
    values.update(overrides)
    return SessionDetails(**values)


@pytest.fixture
def events() -> InMemoryEventRepository:
    return InMemoryEventRepository()


@pytest.fixture
def sessions() -> InMemorySessionRepository:
    return InMemorySessionRepository()


@pytest.fixture
def speakers() -> InMemorySpeakerRepository:
    return InMemorySpeakerRepository()


@pytest.fixture
def unit_of_work() -> SpyUnitOfWork:
    return SpyUnitOfWork()


@pytest.fixture
def policy() -> EventAccessPolicy:
    return EventAccessPolicy(AuthorizationService())


@pytest.fixture
def event(events: InMemoryEventRepository) -> Event:
    return events.add(
        build_event(
            created_by=OWNER.user_id,
            status=EventStatus.DRAFT,
            start_date=_at(0),
            end_date=_at(8),
        )
    )


@pytest.fixture
def speaker(speakers: InMemorySpeakerRepository) -> Speaker:
    return speakers.add(Speaker(name="Grace Hopper"))


@pytest.fixture
def session(sessions: InMemorySessionRepository, event: Event) -> Session:
    return sessions.add(build_session(event_id=event.id, start_time=_at(1), end_time=_at(2)))


class TestCreateSession:
    @pytest.fixture
    def create(
        self,
        sessions: InMemorySessionRepository,
        events: InMemoryEventRepository,
        speakers: InMemorySpeakerRepository,
        policy: EventAccessPolicy,
        unit_of_work: SpyUnitOfWork,
    ) -> CreateSessionUseCase:
        return CreateSessionUseCase(sessions, events, speakers, policy, unit_of_work)

    @pytest.mark.parametrize("actor", [OWNER, ADMIN])
    def test_creates_session_without_speaker(
        self,
        create: CreateSessionUseCase,
        sessions: InMemorySessionRepository,
        unit_of_work: SpyUnitOfWork,
        event: Event,
        actor: Actor,
    ) -> None:
        created = create.execute(actor, CreateSessionCommand(event.id or 0, _details()))

        assert created.id is not None
        stored = sessions.get_by_id(created.id)
        assert stored is not None
        assert SessionView.from_session(stored) == created
        assert (created.event_id, created.speaker_id, created.capacity) == (event.id, None, 40)
        assert created.speaker_name is None
        assert unit_of_work.commits == 1

    def test_creates_session_with_speaker(
        self, create: CreateSessionUseCase, event: Event, speaker: Speaker
    ) -> None:
        created = create.execute(
            OWNER, CreateSessionCommand(event.id or 0, _details(speaker_id=speaker.id))
        )

        assert created.speaker_id == speaker.id
        assert created.speaker_name == "Grace Hopper"

    def test_session_may_span_the_whole_event(
        self, create: CreateSessionUseCase, event: Event
    ) -> None:
        details = _details(start_time=event.start_date, end_time=event.end_date)

        assert create.execute(OWNER, CreateSessionCommand(event.id or 0, details)).id

    def test_rejects_unknown_speaker(
        self, create: CreateSessionUseCase, unit_of_work: SpyUnitOfWork, event: Event
    ) -> None:
        with pytest.raises(NotFoundError, match="Speaker not found"):
            create.execute(OWNER, CreateSessionCommand(event.id or 0, _details(speaker_id=99)))
        assert unit_of_work.commits == 0

    def test_rejects_unknown_event(self, create: CreateSessionUseCase) -> None:
        with pytest.raises(NotFoundError, match="Event not found"):
            create.execute(ADMIN, CreateSessionCommand(999, _details()))

    @pytest.mark.parametrize(
        ("start", "end"),
        [(-0.5, 1), (7.5, 9), (-2, -1), (9, 10)],
        ids=["starts_before", "ends_after", "entirely_before", "entirely_after"],
    )
    def test_rejects_sessions_outside_the_event(
        self, create: CreateSessionUseCase, event: Event, start: float, end: float
    ) -> None:
        details = _details(start_time=_at(start), end_time=_at(end))

        with pytest.raises(InvalidValueError, match="within the event schedule"):
            create.execute(OWNER, CreateSessionCommand(event.id or 0, details))

    @pytest.mark.parametrize("capacity", [1, 100])
    def test_accepts_capacity_up_to_the_event_capacity(
        self, create: CreateSessionUseCase, event: Event, capacity: int
    ) -> None:
        assert event.capacity == 100

        created = create.execute(
            OWNER, CreateSessionCommand(event.id or 0, _details(capacity=capacity))
        )

        assert created.capacity == capacity

    def test_rejects_capacity_above_the_event_capacity_without_saving(
        self,
        create: CreateSessionUseCase,
        sessions: InMemorySessionRepository,
        unit_of_work: SpyUnitOfWork,
        event: Event,
    ) -> None:
        with pytest.raises(InvalidValueError, match="cannot exceed the event capacity"):
            create.execute(OWNER, CreateSessionCommand(event.id or 0, _details(capacity=101)))

        assert sessions.list_by_event(event.id or 0) == []
        assert unit_of_work.commits == 0

    @pytest.mark.parametrize(
        "overrides",
        [
            {"capacity": 0},
            {"capacity": -3},
            {"title": "  "},
            {"start_time": _at(2), "end_time": _at(2)},
            {"start_time": _at(3), "end_time": _at(2)},
        ],
    )
    def test_rejects_invalid_details(
        self, create: CreateSessionUseCase, event: Event, overrides: dict[str, Any]
    ) -> None:
        with pytest.raises(InvalidValueError):
            create.execute(OWNER, CreateSessionCommand(event.id or 0, _details(**overrides)))

    @pytest.mark.parametrize("actor", [OTHER_ORGANIZER, ATTENDEE])
    def test_only_event_managers_can_create(
        self, create: CreateSessionUseCase, event: Event, actor: Actor
    ) -> None:
        with pytest.raises(AuthorizationError):
            create.execute(actor, CreateSessionCommand(event.id or 0, _details()))

    def test_attendee_is_forbidden_before_event_lookup(self, create: CreateSessionUseCase) -> None:
        with pytest.raises(AuthorizationError):
            create.execute(ATTENDEE, CreateSessionCommand(999, _details()))

    @pytest.mark.parametrize("status", [EventStatus.CANCELLED, EventStatus.COMPLETED])
    def test_rejects_final_events(
        self,
        create: CreateSessionUseCase,
        events: InMemoryEventRepository,
        status: EventStatus,
    ) -> None:
        final_event = events.add(
            build_event(created_by=OWNER.user_id, status=status, start_date=_at(0), end_date=_at(8))
        )

        with pytest.raises(EventNotEditableError):
            create.execute(OWNER, CreateSessionCommand(final_event.id or 0, _details()))

    def test_published_events_accept_sessions(
        self, create: CreateSessionUseCase, events: InMemoryEventRepository
    ) -> None:
        published = events.add(
            build_event(created_by=OWNER.user_id, start_date=_at(0), end_date=_at(8))
        )

        assert create.execute(OWNER, CreateSessionCommand(published.id or 0, _details())).id


class TestGetAndListSessions:
    @pytest.fixture
    def get_session(
        self,
        sessions: InMemorySessionRepository,
        events: InMemoryEventRepository,
        speakers: InMemorySpeakerRepository,
        policy: EventAccessPolicy,
    ) -> GetSessionUseCase:
        return GetSessionUseCase(sessions, events, speakers, policy)

    @pytest.fixture
    def list_sessions(
        self,
        sessions: InMemorySessionRepository,
        events: InMemoryEventRepository,
        speakers: InMemorySpeakerRepository,
        policy: EventAccessPolicy,
    ) -> ListEventSessionsUseCase:
        return ListEventSessionsUseCase(sessions, speakers, GetEventUseCase(events, policy))

    @pytest.mark.parametrize("actor", [None, ATTENDEE, OTHER_ORGANIZER])
    def test_sessions_of_unpublished_events_are_hidden(
        self,
        get_session: GetSessionUseCase,
        list_sessions: ListEventSessionsUseCase,
        session: Session,
        event: Event,
        actor: Actor | None,
    ) -> None:
        with pytest.raises(NotFoundError, match="Session not found"):
            get_session.execute(session.id or 0, actor)
        with pytest.raises(NotFoundError, match="Event not found"):
            list_sessions.execute(event.id or 0, actor)

    @pytest.mark.parametrize("actor", [OWNER, ADMIN])
    def test_managers_see_sessions_of_unpublished_events(
        self,
        get_session: GetSessionUseCase,
        list_sessions: ListEventSessionsUseCase,
        session: Session,
        event: Event,
        actor: Actor,
    ) -> None:
        view = SessionView.from_session(session)
        assert get_session.execute(session.id or 0, actor) == view
        assert list_sessions.execute(event.id or 0, actor) == [view]

    def test_sessions_of_published_events_are_public(
        self,
        get_session: GetSessionUseCase,
        list_sessions: ListEventSessionsUseCase,
        events: InMemoryEventRepository,
        sessions: InMemorySessionRepository,
    ) -> None:
        published = events.add(build_event(start_date=_at(0), end_date=_at(8)))
        late = sessions.add(
            build_session(event_id=published.id, start_time=_at(5), end_time=_at(6))
        )
        early = sessions.add(
            build_session(event_id=published.id, start_time=_at(1), end_time=_at(2))
        )

        assert get_session.execute(late.id or 0) == SessionView.from_session(late)
        assert list_sessions.execute(published.id or 0) == [
            SessionView.from_session(early),
            SessionView.from_session(late),
        ]

    def test_includes_the_speaker_name_and_none_without_speaker(
        self,
        get_session: GetSessionUseCase,
        list_sessions: ListEventSessionsUseCase,
        sessions: InMemorySessionRepository,
        speakers: InMemorySpeakerRepository,
        event: Event,
    ) -> None:
        grace = speakers.add(Speaker(name="Grace Hopper"))
        with_speaker = sessions.add(
            build_session(
                event_id=event.id, speaker_id=grace.id, start_time=_at(1), end_time=_at(2)
            )
        )
        without_speaker = sessions.add(
            build_session(event_id=event.id, start_time=_at(3), end_time=_at(4))
        )

        listed = list_sessions.execute(event.id or 0, OWNER)

        assert [(view.id, view.speaker_id, view.speaker_name) for view in listed] == [
            (with_speaker.id, grace.id, "Grace Hopper"),
            (without_speaker.id, None, None),
        ]
        assert get_session.execute(with_speaker.id or 0, OWNER).speaker_name == "Grace Hopper"

    def test_unknown_session_or_event(
        self, get_session: GetSessionUseCase, list_sessions: ListEventSessionsUseCase
    ) -> None:
        with pytest.raises(NotFoundError, match="Session not found"):
            get_session.execute(999, ADMIN)
        with pytest.raises(NotFoundError, match="Event not found"):
            list_sessions.execute(999, ADMIN)


class TestUpdateSession:
    @pytest.fixture
    def update(
        self,
        sessions: InMemorySessionRepository,
        events: InMemoryEventRepository,
        speakers: InMemorySpeakerRepository,
        policy: EventAccessPolicy,
        unit_of_work: SpyUnitOfWork,
    ) -> UpdateSessionUseCase:
        return UpdateSessionUseCase(sessions, events, speakers, policy, unit_of_work)

    @pytest.mark.parametrize("actor", [OWNER, ADMIN])
    def test_updates_details_and_speaker(
        self,
        update: UpdateSessionUseCase,
        session: Session,
        speaker: Speaker,
        unit_of_work: SpyUnitOfWork,
        actor: Actor,
    ) -> None:
        details = _details(title="Renamed", capacity=15, speaker_id=speaker.id)

        updated = update.execute(actor, UpdateSessionCommand(session.id or 0, details))

        assert (updated.title, updated.capacity, updated.speaker_id) == ("Renamed", 15, speaker.id)
        assert updated.speaker_name == speaker.name
        assert (updated.id, updated.event_id) == (session.id, session.event_id)
        assert unit_of_work.commits == 1

    def test_speaker_can_be_removed(
        self,
        update: UpdateSessionUseCase,
        sessions: InMemorySessionRepository,
        event: Event,
        speaker: Speaker,
    ) -> None:
        with_speaker = sessions.add(build_session(event_id=event.id, speaker_id=speaker.id))

        updated = update.execute(OWNER, UpdateSessionCommand(with_speaker.id or 0, _details()))

        assert updated.speaker_id is None

    @pytest.mark.parametrize("actor", [OTHER_ORGANIZER, ATTENDEE])
    def test_only_event_managers_can_update(
        self, update: UpdateSessionUseCase, session: Session, actor: Actor
    ) -> None:
        with pytest.raises(AuthorizationError):
            update.execute(actor, UpdateSessionCommand(session.id or 0, _details()))

    def test_rejects_schedule_outside_event(
        self, update: UpdateSessionUseCase, session: Session
    ) -> None:
        details = _details(start_time=_at(7), end_time=_at(9))

        with pytest.raises(InvalidValueError, match="within the event schedule"):
            update.execute(OWNER, UpdateSessionCommand(session.id or 0, details))

    def test_accepts_capacity_equal_to_the_event_capacity(
        self, update: UpdateSessionUseCase, session: Session
    ) -> None:
        updated = update.execute(
            OWNER, UpdateSessionCommand(session.id or 0, _details(capacity=100))
        )

        assert updated.capacity == 100

    def test_rejects_capacity_above_the_event_capacity_without_saving(
        self,
        update: UpdateSessionUseCase,
        sessions: InMemorySessionRepository,
        unit_of_work: SpyUnitOfWork,
        session: Session,
    ) -> None:
        with pytest.raises(InvalidValueError, match="cannot exceed the event capacity"):
            update.execute(OWNER, UpdateSessionCommand(session.id or 0, _details(capacity=101)))

        stored = sessions.get_by_id(session.id or 0)
        assert stored is not None
        assert stored.capacity == session.capacity
        assert unit_of_work.commits == 0

    def test_rejects_unknown_speaker(self, update: UpdateSessionUseCase, session: Session) -> None:
        with pytest.raises(NotFoundError, match="Speaker not found"):
            update.execute(OWNER, UpdateSessionCommand(session.id or 0, _details(speaker_id=42)))

    def test_rejects_unknown_session(self, update: UpdateSessionUseCase) -> None:
        with pytest.raises(NotFoundError, match="Session not found"):
            update.execute(ADMIN, UpdateSessionCommand(999, _details()))

    def test_rejects_sessions_of_final_events(
        self,
        update: UpdateSessionUseCase,
        events: InMemoryEventRepository,
        sessions: InMemorySessionRepository,
    ) -> None:
        cancelled = events.add(
            build_event(
                created_by=OWNER.user_id,
                status=EventStatus.CANCELLED,
                start_date=_at(0),
                end_date=_at(8),
            )
        )
        stored = sessions.add(build_session(event_id=cancelled.id))

        with pytest.raises(EventNotEditableError):
            update.execute(OWNER, UpdateSessionCommand(stored.id or 0, _details()))


class TestDeleteSession:
    @pytest.fixture
    def delete(
        self,
        sessions: InMemorySessionRepository,
        events: InMemoryEventRepository,
        policy: EventAccessPolicy,
        unit_of_work: SpyUnitOfWork,
    ) -> DeleteSessionUseCase:
        return DeleteSessionUseCase(sessions, events, policy, unit_of_work)

    @pytest.mark.parametrize("actor", [OWNER, ADMIN])
    def test_deletes_session(
        self,
        delete: DeleteSessionUseCase,
        sessions: InMemorySessionRepository,
        session: Session,
        unit_of_work: SpyUnitOfWork,
        actor: Actor,
    ) -> None:
        delete.execute(actor, session.id or 0)

        assert sessions.get_by_id(session.id or 0) is None
        assert unit_of_work.commits == 1

    @pytest.mark.parametrize("actor", [OTHER_ORGANIZER, ATTENDEE])
    def test_only_event_managers_can_delete(
        self,
        delete: DeleteSessionUseCase,
        sessions: InMemorySessionRepository,
        session: Session,
        actor: Actor,
    ) -> None:
        with pytest.raises(AuthorizationError):
            delete.execute(actor, session.id or 0)
        assert sessions.get_by_id(session.id or 0) == session

    def test_rejects_unknown_session(self, delete: DeleteSessionUseCase) -> None:
        with pytest.raises(NotFoundError, match="Session not found"):
            delete.execute(ADMIN, 999)

    def test_rejects_sessions_of_final_events(
        self,
        delete: DeleteSessionUseCase,
        events: InMemoryEventRepository,
        sessions: InMemorySessionRepository,
    ) -> None:
        completed = events.add(
            build_event(
                created_by=OWNER.user_id,
                status=EventStatus.COMPLETED,
                start_date=_at(0),
                end_date=_at(8),
            )
        )
        stored = sessions.add(build_session(event_id=completed.id))

        with pytest.raises(EventNotEditableError):
            delete.execute(OWNER, stored.id or 0)
