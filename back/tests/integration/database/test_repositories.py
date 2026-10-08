from dataclasses import replace
from datetime import timedelta

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.domain.entities import Event, Registration, Speaker, User
from app.domain.enums import EventStatus
from app.domain.exceptions import (
    AlreadyRegisteredToEventError,
    EmailAlreadyRegisteredError,
    NotFoundError,
)
from app.domain.ports import EventSearchCriteria, EventVisibility
from app.domain.value_objects import PageRequest
from app.infrastructure.database.models import EventModel
from app.infrastructure.database.repositories import (
    SqlAlchemyEventRepository,
    SqlAlchemyRegistrationRepository,
    SqlAlchemySessionRepository,
    SqlAlchemySpeakerRepository,
    SqlAlchemyUserRepository,
)
from tests.factories import EVENT_START, build_event, build_session, build_user

PUBLIC = EventVisibility.public()


@pytest.fixture
def users(db_session: Session) -> SqlAlchemyUserRepository:
    return SqlAlchemyUserRepository(db_session)


@pytest.fixture
def events(db_session: Session) -> SqlAlchemyEventRepository:
    return SqlAlchemyEventRepository(db_session)


@pytest.fixture
def registrations(db_session: Session) -> SqlAlchemyRegistrationRepository:
    return SqlAlchemyRegistrationRepository(db_session)


@pytest.fixture
def speakers(db_session: Session) -> SqlAlchemySpeakerRepository:
    return SqlAlchemySpeakerRepository(db_session)


@pytest.fixture
def sessions(db_session: Session) -> SqlAlchemySessionRepository:
    return SqlAlchemySessionRepository(db_session)


@pytest.fixture
def creator(users: SqlAlchemyUserRepository) -> User:
    return users.add(build_user(email="organizer@example.com"))


@pytest.fixture
def event(events: SqlAlchemyEventRepository, creator: User) -> Event:
    return events.add(build_event(created_by=creator.id))


class TestUserRepository:
    def test_add_assigns_id_and_timestamps(self, users: SqlAlchemyUserRepository) -> None:
        user = users.add(build_user())

        assert user.id is not None
        assert user.created_at is not None
        assert user.updated_at is not None
        assert users.get_by_id(user.id) == user

    def test_get_by_email(self, users: SqlAlchemyUserRepository) -> None:
        user = users.add(build_user())

        assert users.get_by_email("ada@example.com") == user
        assert users.get_by_email("missing@example.com") is None

    def test_unique_email_is_enforced_by_the_database(
        self, users: SqlAlchemyUserRepository
    ) -> None:
        users.add(build_user())

        with pytest.raises(EmailAlreadyRegisteredError):
            users.add(build_user(name="Impostor"))


class TestEventRepository:
    def test_update_persists_changes(self, events: SqlAlchemyEventRepository, event: Event) -> None:
        updated = events.update(replace(event, name="Renamed", status=EventStatus.CANCELLED))

        assert events.get_by_id(updated.id) == updated
        assert updated.name == "Renamed"
        assert updated.status is EventStatus.CANCELLED

    def test_update_and_delete_missing_event_raise_not_found(
        self, events: SqlAlchemyEventRepository, event: Event
    ) -> None:
        with pytest.raises(NotFoundError, match="Event not found"):
            events.update(replace(event, id=999_999))
        with pytest.raises(NotFoundError, match="Event not found"):
            events.delete(999_999)

    def test_delete_cascades_to_sessions_and_registrations(
        self,
        events: SqlAlchemyEventRepository,
        sessions: SqlAlchemySessionRepository,
        registrations: SqlAlchemyRegistrationRepository,
        event: Event,
        creator: User,
    ) -> None:
        session = sessions.add(build_session(event_id=event.id))
        registrations.add(Registration(user_id=creator.id, event_id=event.id))

        events.delete(event.id)

        assert events.get_by_id(event.id) is None
        assert sessions.get_by_id(session.id) is None
        assert registrations.count_by_event(event.id) == 0

    def test_get_by_id_for_update_locks_the_row(
        self, events: SqlAlchemyEventRepository, event: Event, db_session: Session
    ) -> None:
        locked = events.get_by_id_for_update(event.id)

        lock_modes = set(
            db_session.scalars(
                text(
                    "SELECT mode FROM pg_locks "
                    "WHERE relation = 'events'::regclass AND pid = pg_backend_pid()"
                )
            )
        )
        assert locked == event
        assert "RowShareLock" in lock_modes
        assert events.get_by_id_for_update(999_999) is None

    @pytest.mark.parametrize("term", ["python", "Python", "PYTHON", "thon"])
    def test_search_matches_part_of_the_name_case_insensitively(
        self, events: SqlAlchemyEventRepository, creator: User, term: str
    ) -> None:
        for name in ["Python Conference", "Advanced python", "PYTHON Backend Workshop"]:
            events.add(build_event(name=name, created_by=creator.id))
        events.add(build_event(name="Data", description="Using python", created_by=creator.id))
        events.add(build_event(name="Meetup", location="Python House", created_by=creator.id))

        page = events.search(EventSearchCriteria(PUBLIC, name=term), PageRequest())

        assert {event.name for event in page.items} == {
            "Python Conference",
            "Advanced python",
            "PYTHON Backend Workshop",
        }

    def test_visibility_restricts_unpublished_events(
        self, events: SqlAlchemyEventRepository, users: SqlAlchemyUserRepository, creator: User
    ) -> None:
        other = users.add(build_user(email="other@example.com"))
        events.add(build_event(name="Public", created_by=other.id))
        events.add(build_event(name="Mine", created_by=creator.id, status=EventStatus.DRAFT))
        events.add(build_event(name="Theirs", created_by=other.id, status=EventStatus.CANCELLED))

        def names(visibility: EventVisibility) -> set[str]:
            page = events.search(EventSearchCriteria(visibility), PageRequest())
            return {event.name for event in page.items}

        assert names(PUBLIC) == {"Public"}
        assert names(EventVisibility.public_or_owned_by(creator.id)) == {"Public", "Mine"}
        assert names(EventVisibility.unrestricted()) == {"Public", "Mine", "Theirs"}

    @pytest.mark.parametrize(
        "malicious", ["' OR '1'='1", "%", "_", "'; DROP TABLE events; --", "\\"]
    )
    def test_search_treats_input_as_literal_text(
        self,
        events: SqlAlchemyEventRepository,
        event: Event,
        db_session: Session,
        malicious: str,
    ) -> None:
        page = events.search(EventSearchCriteria(PUBLIC, name=malicious), PageRequest())

        assert page.total == 0
        assert db_session.scalar(select(func.count()).select_from(EventModel)) == 1

    def test_search_filters_by_status_and_paginates(
        self, events: SqlAlchemyEventRepository, creator: User
    ) -> None:
        for day in range(5):
            events.add(
                build_event(
                    name=f"Event {day}",
                    created_by=creator.id,
                    start_date=EVENT_START + timedelta(days=day),
                    end_date=EVENT_START + timedelta(days=day, hours=1),
                )
            )
        events.add(build_event(name="Hidden", created_by=creator.id, status=EventStatus.DRAFT))

        page = events.search(
            EventSearchCriteria(EventVisibility.unrestricted(), status=EventStatus.PUBLISHED),
            PageRequest(page=2, per_page=2),
        )

        assert [event.name for event in page.items] == ["Event 2", "Event 3"]
        assert (page.total, page.pages) == (5, 3)

    def test_list_by_attendee_returns_registered_events(
        self,
        events: SqlAlchemyEventRepository,
        registrations: SqlAlchemyRegistrationRepository,
        users: SqlAlchemyUserRepository,
        event: Event,
        creator: User,
    ) -> None:
        events.add(build_event(name="Not registered", created_by=creator.id))
        attendee = users.add(build_user(email="attendee@example.com"))
        registrations.add(Registration(user_id=attendee.id, event_id=event.id))

        assert events.list_by_attendee(attendee.id) == [event]


class TestRegistrationRepository:
    def test_add_get_count_and_delete(
        self, registrations: SqlAlchemyRegistrationRepository, event: Event, creator: User
    ) -> None:
        registration = registrations.add(Registration(user_id=creator.id, event_id=event.id))

        assert registration.registered_at is not None
        assert registrations.get(creator.id, event.id) == registration
        assert registrations.count_by_event(event.id) == 1

        registrations.delete(registration.id)

        assert registrations.get(creator.id, event.id) is None
        assert registrations.count_by_event(event.id) == 0

    def test_duplicate_registration_is_rejected_by_the_database(
        self, registrations: SqlAlchemyRegistrationRepository, event: Event, creator: User
    ) -> None:
        registrations.add(Registration(user_id=creator.id, event_id=event.id))

        with pytest.raises(AlreadyRegisteredToEventError):
            registrations.add(Registration(user_id=creator.id, event_id=event.id))


class TestSpeakerAndSessionRepositories:
    def test_list_speakers_is_paginated_and_sorted_by_name(
        self, speakers: SqlAlchemySpeakerRepository
    ) -> None:
        for name in ["Grace", "Alan", "Barbara"]:
            speakers.add(Speaker(name=name))

        page = speakers.list_all(PageRequest(page=1, per_page=2))

        assert [speaker.name for speaker in page.items] == ["Alan", "Barbara"]
        assert page.total == 3

    def test_update_speaker(self, speakers: SqlAlchemySpeakerRepository) -> None:
        speaker = speakers.add(Speaker(name="Grace"))

        updated = speakers.update(replace(speaker, bio="Compiler pioneer"))

        assert speakers.get_by_id(speaker.id) == updated
        assert updated.bio == "Compiler pioneer"

    def test_sessions_are_listed_by_start_time(
        self, sessions: SqlAlchemySessionRepository, event: Event
    ) -> None:
        late = sessions.add(
            build_session(
                event_id=event.id,
                title="Late",
                start_time=EVENT_START + timedelta(hours=5),
                end_time=EVENT_START + timedelta(hours=6),
            )
        )
        early = sessions.add(build_session(event_id=event.id, title="Early"))

        assert sessions.list_by_event(event.id) == [early, late]

    def test_deleting_speaker_keeps_session_without_speaker(
        self,
        speakers: SqlAlchemySpeakerRepository,
        sessions: SqlAlchemySessionRepository,
        event: Event,
        db_session: Session,
    ) -> None:
        speaker = speakers.add(Speaker(name="Grace"))
        session = sessions.add(build_session(event_id=event.id, speaker_id=speaker.id))

        speakers.delete(speaker.id)
        db_session.expire_all()

        remaining = sessions.get_by_id(session.id)
        assert remaining is not None
        assert remaining.speaker_id is None
