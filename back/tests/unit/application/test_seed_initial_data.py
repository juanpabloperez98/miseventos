import logging
from dataclasses import replace
from datetime import UTC, datetime

import pytest

from app.application.dto import SeedInitialDataCommand, SeedUser
from app.application.use_cases.seeding import DEFAULT_CATALOG, SeedInitialDataUseCase
from app.domain.entities import User
from app.domain.enums import EventStatus, UserRole
from app.domain.exceptions import InvalidValueError
from app.domain.ports import SeedEntityType
from app.infrastructure.security import Sha256PasswordHasher
from tests.unit.application.fakes import (
    InMemoryEventRepository,
    InMemorySeedRecordRepository,
    InMemorySessionRepository,
    InMemorySpeakerRepository,
    InMemoryUserRepository,
    SpyUnitOfWork,
)

NOW = datetime(2030, 3, 15, 18, 30, tzinfo=UTC)
ADMIN = SeedUser(
    name="Admin Seed", email=" Admin@Example.com ", password="admin-password", role=UserRole.ADMIN
)
ORGANIZER = SeedUser(
    name="Organizer Seed",
    email="organizer@example.com",
    password="organizer-password",
    role=UserRole.ORGANIZER,
)
ATTENDEE = SeedUser(
    name="Attendee Seed",
    email="attendee@example.com",
    password="attendee-password",
    role=UserRole.ATTENDEE,
)
FULL_SEED = SeedInitialDataCommand(users=(ADMIN, ORGANIZER, ATTENDEE), demo_data=True)
DEMO_RECORDS = (
    len(DEFAULT_CATALOG.speakers) + len(DEFAULT_CATALOG.events) + len(DEFAULT_CATALOG.sessions)
)


class Seeder:
    def __init__(self) -> None:
        self.users = InMemoryUserRepository()
        self.speakers = InMemorySpeakerRepository()
        self.events = InMemoryEventRepository()
        self.sessions = InMemorySessionRepository()
        self.seed_records = InMemorySeedRecordRepository()
        self.hasher = Sha256PasswordHasher()
        self.unit_of_work = SpyUnitOfWork()
        self.use_case = SeedInitialDataUseCase(
            self.users,
            self.speakers,
            self.events,
            self.sessions,
            self.seed_records,
            self.hasher,
            self.unit_of_work,
            clock=lambda: NOW,
        )

    def all_events(self) -> list[int]:
        return sorted(self.events._events)

    def all_sessions(self) -> list[int]:
        return sorted(self.sessions._sessions)

    def record_id(self, seed_key: str) -> int:
        record = self.seed_records.get(seed_key)
        assert record is not None
        return record.entity_id


@pytest.fixture
def seeder() -> Seeder:
    return Seeder()


def test_first_run_creates_users_and_demo_data(seeder: Seeder) -> None:
    report = seeder.use_case.execute(FULL_SEED)

    assert report.users_created == 3
    assert report.records_created == DEMO_RECORDS
    assert report.records_existing == 0
    assert seeder.unit_of_work.commits == 1
    for seed in (ADMIN, ORGANIZER, ATTENDEE):
        user = seeder.users.get_by_email(seed.email.strip().lower())
        assert user is not None
        assert user.role is seed.role
        assert user.name == seed.name
    assert len(seeder.speakers._speakers) == len(DEFAULT_CATALOG.speakers)
    assert len(seeder.all_events()) == len(DEFAULT_CATALOG.events)
    assert len(seeder.all_sessions()) == len(DEFAULT_CATALOG.sessions)
    assert len(seeder.seed_records.records) == DEMO_RECORDS


def test_second_run_does_not_duplicate_anything(seeder: Seeder) -> None:
    seeder.use_case.execute(FULL_SEED)
    events, sessions = seeder.all_events(), seeder.all_sessions()

    report = seeder.use_case.execute(FULL_SEED)

    assert report.users_created == 0
    assert report.users_existing == 3
    assert report.records_created == 0
    assert report.records_existing == DEMO_RECORDS
    assert len(seeder.users._users) == 3
    assert len(seeder.speakers._speakers) == len(DEFAULT_CATALOG.speakers)
    assert seeder.all_events() == events
    assert seeder.all_sessions() == sessions


def test_existing_user_keeps_role_name_and_password(
    seeder: Seeder, caplog: pytest.LogCaptureFixture
) -> None:
    original = seeder.users.add(
        User(
            name="Someone Else",
            email="admin@example.com",
            password_hash=seeder.hasher.hash("original-password"),
            role=UserRole.ATTENDEE,
        )
    )

    with caplog.at_level(logging.WARNING):
        report = seeder.use_case.execute(SeedInitialDataCommand(users=(ADMIN,)))

    stored = seeder.users.get_by_email("admin@example.com")
    assert stored == original
    assert stored.role is UserRole.ATTENDEE
    assert stored.name == "Someone Else"
    assert seeder.hasher.verify("original-password", stored.password_hash)
    assert not seeder.hasher.verify(ADMIN.password, stored.password_hash)
    assert report.users_created == 0
    assert report.users_existing == 1
    assert [record.message for record in caplog.records] == ["seed_user_role_mismatch"]


def test_passwords_are_stored_with_the_password_hasher(seeder: Seeder) -> None:
    seeder.use_case.execute(FULL_SEED)

    for seed in (ADMIN, ORGANIZER, ATTENDEE):
        user = seeder.users.get_by_email(seed.email.strip().lower())
        assert user is not None
        assert user.password_hash != seed.password
        assert seed.password not in user.password_hash
        assert seeder.hasher.verify(seed.password, user.password_hash)


def test_logs_never_contain_passwords_or_hashes(
    seeder: Seeder, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.DEBUG):
        seeder.use_case.execute(FULL_SEED)

    logged = " ".join(f"{record.getMessage()} {record.__dict__}" for record in caplog.records)
    for seed in (ADMIN, ORGANIZER, ATTENDEE):
        user = seeder.users.get_by_email(seed.email.strip().lower())
        assert user is not None
        assert seed.password not in logged
        assert user.password_hash not in logged


def test_recreates_only_a_deleted_seed_event(seeder: Seeder) -> None:
    seeder.use_case.execute(FULL_SEED)
    deleted_id = seeder.record_id("event:cloud-devops-meetup")
    other_events = [event_id for event_id in seeder.all_events() if event_id != deleted_id]
    seeder.events.delete(deleted_id)

    report = seeder.use_case.execute(FULL_SEED)

    recreated_id = seeder.record_id("event:cloud-devops-meetup")
    assert report.records_created == 1
    assert recreated_id != deleted_id
    assert seeder.all_events() == [*other_events, recreated_id]
    assert len(seeder.all_sessions()) == len(DEFAULT_CATALOG.sessions)


def test_recreates_only_a_deleted_seed_session(seeder: Seeder) -> None:
    seeder.use_case.execute(FULL_SEED)
    deleted_id = seeder.record_id("session:angular-frontend-day:testing")
    seeder.sessions.delete(deleted_id)

    report = seeder.use_case.execute(FULL_SEED)

    recreated = seeder.sessions.get_by_id(seeder.record_id("session:angular-frontend-day:testing"))
    assert report.records_created == 1
    assert recreated is not None
    assert recreated.event_id == seeder.record_id("event:angular-frontend-day")
    assert len(seeder.all_sessions()) == len(DEFAULT_CATALOG.sessions)


def test_keeps_manual_changes_to_seed_records(seeder: Seeder) -> None:
    seeder.use_case.execute(FULL_SEED)
    event = seeder.events.get_by_id(seeder.record_id("event:bogota-python-summit"))
    assert event is not None
    seeder.events.update(replace(event, name="Renamed by an organizer", capacity=10))

    report = seeder.use_case.execute(FULL_SEED)

    stored = seeder.events.get_by_id(event.id or 0)
    assert stored is not None
    assert stored.name == "Renamed by an organizer"
    assert stored.capacity == 10
    assert report.records_created == 0


def test_skips_a_missing_session_that_no_longer_fits_its_edited_event(
    seeder: Seeder, caplog: pytest.LogCaptureFixture
) -> None:
    seeder.use_case.execute(FULL_SEED)
    event = seeder.events.get_by_id(seeder.record_id("event:angular-frontend-day"))
    assert event is not None
    seeder.events.update(
        replace(event, end_date=event.start_date + (event.end_date - event.start_date) / 4)
    )
    seeder.sessions.delete(seeder.record_id("session:angular-frontend-day:testing"))

    with caplog.at_level(logging.WARNING):
        report = seeder.use_case.execute(FULL_SEED)

    assert report.records_skipped == 1
    assert report.records_created == 0
    assert len(seeder.all_sessions()) == len(DEFAULT_CATALOG.sessions) - 1
    assert "seed_session_skipped" in [record.message for record in caplog.records]


def test_demo_data_is_owned_by_the_seed_organizer_and_respects_domain_rules(
    seeder: Seeder,
) -> None:
    seeder.use_case.execute(FULL_SEED)
    organizer = seeder.users.get_by_email(ORGANIZER.email)
    assert organizer is not None

    events = [seeder.events.get_by_id(event_id) for event_id in seeder.all_events()]
    statuses = {event.status for event in events if event is not None}
    assert {EventStatus.DRAFT, EventStatus.PUBLISHED} <= statuses
    for event in events:
        assert event is not None
        assert event.created_by == organizer.id
        assert event.capacity > 0
        assert event.start_date.tzinfo is not None
        assert event.start_date < event.end_date

    published = [event for event in events if event and event.status is EventStatus.PUBLISHED]
    assert published
    assert all(event.start_date > NOW for event in published)

    for session_id in seeder.all_sessions():
        session = seeder.sessions.get_by_id(session_id)
        assert session is not None
        event = seeder.events.get_by_id(session.event_id)
        assert event is not None
        session.ensure_fits_within(event)
        assert session.capacity > 0
        assert session.speaker_id is None or seeder.speakers.get_by_id(session.speaker_id)


def test_seed_records_point_to_real_entities(seeder: Seeder) -> None:
    seeder.use_case.execute(FULL_SEED)

    finders = {
        SeedEntityType.SPEAKER: seeder.speakers.get_by_id,
        SeedEntityType.EVENT: seeder.events.get_by_id,
        SeedEntityType.SESSION: seeder.sessions.get_by_id,
    }
    for record in seeder.seed_records.records.values():
        assert finders[record.entity_type](record.entity_id) is not None


def test_skips_demo_data_when_the_organizer_email_belongs_to_another_role(
    seeder: Seeder, caplog: pytest.LogCaptureFixture
) -> None:
    seeder.users.add(
        User(
            name="Existing Attendee",
            email=ORGANIZER.email,
            password_hash=seeder.hasher.hash("whatever-password"),
        )
    )

    with caplog.at_level(logging.WARNING):
        report = seeder.use_case.execute(FULL_SEED)

    assert report.demo_data_skipped
    assert seeder.all_events() == []
    assert seeder.seed_records.records == {}
    assert "seed_demo_data_skipped" in [record.message for record in caplog.records]


def test_demo_data_requires_a_seed_organizer(seeder: Seeder) -> None:
    with pytest.raises(InvalidValueError, match="ORGANIZER"):
        seeder.use_case.execute(SeedInitialDataCommand(users=(ADMIN,), demo_data=True))

    assert seeder.users._users == {}


def test_failure_rolls_back_and_propagates(seeder: Seeder) -> None:
    def broken_add(*_: object) -> None:
        raise RuntimeError("database unavailable")

    seeder.events.add = broken_add  # type: ignore[method-assign,assignment]

    with pytest.raises(RuntimeError, match="database unavailable"):
        seeder.use_case.execute(FULL_SEED)

    assert seeder.unit_of_work.commits == 0
    assert seeder.unit_of_work.rollbacks == 1


def test_nothing_is_created_when_every_seed_is_disabled(seeder: Seeder) -> None:
    report = seeder.use_case.execute(SeedInitialDataCommand())

    assert report.users_created == 0
    assert report.records_created == 0
    assert seeder.users._users == {}
