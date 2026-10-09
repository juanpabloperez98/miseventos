from dataclasses import replace

import pytest
from click.testing import Result
from flask import Flask
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.application.use_cases.seeding import DEFAULT_CATALOG, SeedInitialDataUseCase
from app.bootstrap import create_app
from app.container import Container, RequestScope
from app.domain.enums import EventStatus, UserRole
from app.domain.ports import SeedEntityType
from app.infrastructure.config import Environment, Settings
from app.infrastructure.database.base import Base
from app.infrastructure.database.models import (
    EventModel,
    RegistrationModel,
    SeedRecordModel,
    SessionModel,
    SpeakerModel,
    UserModel,
)

SEED_ENV = {
    "SEED_ADMIN_ENABLED": "true",
    "SEED_ADMIN_NAME": "Admin Mis Eventos",
    "SEED_ADMIN_EMAIL": "admin@example.com",
    "SEED_ADMIN_PASSWORD": "admin-test-password",
    "SEED_ORGANIZER_ENABLED": "true",
    "SEED_ORGANIZER_NAME": "Organizer Mis Eventos",
    "SEED_ORGANIZER_EMAIL": "organizer@example.com",
    "SEED_ORGANIZER_PASSWORD": "organizer-test-password",
    "SEED_ATTENDEE_ENABLED": "true",
    "SEED_ATTENDEE_NAME": "Attendee Mis Eventos",
    "SEED_ATTENDEE_EMAIL": "attendee@example.com",
    "SEED_ATTENDEE_PASSWORD": "attendee-test-password",
    "SEED_DEMO_DATA_ENABLED": "true",
}
SEEDED_TABLES: tuple[type[Base], ...] = (
    UserModel,
    SpeakerModel,
    EventModel,
    SessionModel,
    SeedRecordModel,
    RegistrationModel,
)
DEMO_RECORDS = (
    len(DEFAULT_CATALOG.speakers) + len(DEFAULT_CATALOG.events) + len(DEFAULT_CATALOG.sessions)
)
MODEL_BY_ENTITY_TYPE: dict[SeedEntityType, type[Base]] = {
    SeedEntityType.SPEAKER: SpeakerModel,
    SeedEntityType.EVENT: EventModel,
    SeedEntityType.SESSION: SessionModel,
}


@pytest.fixture(autouse=True)
def seed_env(monkeypatch: pytest.MonkeyPatch) -> None:
    # Keep the tests independent from the values in the local .env file.
    monkeypatch.setattr("app.infrastructure.config.seed_settings.load_dotenv", lambda: False)
    for key, value in SEED_ENV.items():
        monkeypatch.setenv(key, value)


def _seed(app: Flask) -> Result:
    return app.test_cli_runner().invoke(args=["seed-initial-data"])


def _counts(db_session: Session) -> dict[str, int]:
    db_session.expire_all()
    return {
        model.__tablename__: db_session.scalar(select(func.count()).select_from(model)) or 0
        for model in SEEDED_TABLES
    }


def _user(db_session: Session, email: str) -> UserModel:
    db_session.expire_all()
    return db_session.scalars(select(UserModel).where(UserModel.email == email)).one()


def test_creating_the_app_does_not_seed(db_app: Flask, db_session: Session) -> None:
    assert "seed-initial-data" in db_app.cli.commands
    assert set(_counts(db_session).values()) == {0}


def test_first_run_creates_users_and_demo_data(db_app: Flask, db_session: Session) -> None:
    result = _seed(db_app)

    assert result.exit_code == 0, result.output
    assert "users created=3" in result.output
    assert _counts(db_session) == {
        "users": 3,
        "speakers": len(DEFAULT_CATALOG.speakers),
        "events": len(DEFAULT_CATALOG.events),
        "sessions": len(DEFAULT_CATALOG.sessions),
        "seed_records": DEMO_RECORDS,
        "registrations": 0,
    }
    for role in UserRole:
        assert _user(db_session, SEED_ENV[f"SEED_{role.value}_EMAIL"]).role is role


def test_repeated_runs_do_not_duplicate_records(db_app: Flask, db_session: Session) -> None:
    assert _seed(db_app).exit_code == 0
    after_first_run = _counts(db_session)

    for _ in range(2):
        result = _seed(db_app)
        assert result.exit_code == 0, result.output
        assert "users created=0 existing=3" in result.output
        assert f"demo records created=0 existing={DEMO_RECORDS}" in result.output

    assert _counts(db_session) == after_first_run


def test_passwords_are_hashed_with_the_password_hasher(db_app: Flask, db_session: Session) -> None:
    container: Container = db_app.extensions["container"]
    _seed(db_app)

    for role in UserRole:
        password = SEED_ENV[f"SEED_{role.value}_PASSWORD"]
        user = _user(db_session, SEED_ENV[f"SEED_{role.value}_EMAIL"])
        assert password not in user.password_hash
        assert container.password_hasher.verify(password, user.password_hash)


def test_existing_user_keeps_name_role_and_password(
    db_app: Flask, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    _seed(db_app)
    admin = _user(db_session, "admin@example.com")
    original = (admin.name, admin.role, admin.password_hash)

    monkeypatch.setenv("SEED_ADMIN_NAME", "Another Name")
    monkeypatch.setenv("SEED_ADMIN_PASSWORD", "another-password")
    result = _seed(db_app)

    assert result.exit_code == 0, result.output
    admin = _user(db_session, "admin@example.com")
    assert (admin.name, admin.role, admin.password_hash) == original


def test_existing_email_is_not_promoted(db_app: Flask, db_session: Session) -> None:
    response = db_app.test_client().post(
        "/api/auth/register",
        json={"name": "Public User", "email": "Admin@Example.com", "password": "public-password"},
    )
    assert response.status_code == 201

    result = _seed(db_app)

    assert result.exit_code == 0, result.output
    user = _user(db_session, "admin@example.com")
    assert user.role is UserRole.ATTENDEE
    assert user.name == "Public User"


def test_public_registration_still_creates_attendees_after_seeding(db_app: Flask) -> None:
    _seed(db_app)

    response = db_app.test_client().post(
        "/api/auth/register",
        json={"name": "New User", "email": "new.user@example.com", "password": "new-password"},
    )

    assert response.status_code == 201
    assert response.get_json()["role"] == UserRole.ATTENDEE.value


def test_recreates_only_a_deleted_seed_event_and_its_sessions(
    db_app: Flask, db_session: Session
) -> None:
    _seed(db_app)
    before = _counts(db_session)
    draft = db_session.scalars(
        select(EventModel).where(EventModel.status == EventStatus.DRAFT)
    ).one()
    draft_sessions = len(draft.sessions)
    untouched_ids = set(db_session.scalars(select(EventModel.id).where(EventModel.id != draft.id)))
    db_session.delete(draft)
    db_session.commit()

    result = _seed(db_app)

    assert result.exit_code == 0, result.output
    assert f"demo records created={1 + draft_sessions}" in result.output
    assert _counts(db_session) == before
    assert untouched_ids < set(db_session.scalars(select(EventModel.id)))


def test_keeps_manual_changes_to_seed_events(db_app: Flask, db_session: Session) -> None:
    _seed(db_app)
    event = db_session.scalars(
        select(EventModel).where(EventModel.status == EventStatus.PUBLISHED)
    ).first()
    assert event is not None
    event_id = event.id
    event.name = "Edited manually"
    event.status = EventStatus.CANCELLED
    db_session.commit()

    result = _seed(db_app)

    assert result.exit_code == 0, result.output
    db_session.expire_all()
    stored = db_session.get(EventModel, event_id)
    assert stored is not None
    assert (stored.name, stored.status) == ("Edited manually", EventStatus.CANCELLED)
    assert "demo records created=0" in result.output


def test_demo_relations_use_real_ids(db_app: Flask, db_session: Session) -> None:
    _seed(db_app)
    organizer = _user(db_session, "organizer@example.com")

    events = db_session.scalars(select(EventModel)).all()
    assert {event.created_by for event in events} == {organizer.id}
    assert {EventStatus.DRAFT, EventStatus.PUBLISHED} <= {event.status for event in events}
    for session in db_session.scalars(select(SessionModel)):
        assert session.event.start_date <= session.start_time < session.end_time
        assert session.end_time <= session.event.end_date
        assert session.speaker is not None
    for record in db_session.scalars(select(SeedRecordModel)):
        model = MODEL_BY_ENTITY_TYPE[record.entity_type]
        assert db_session.get(model, record.entity_id) is not None


def test_refuses_to_run_in_production(
    settings: Settings, session_factory: sessionmaker[Session], db_session: Session
) -> None:
    app = create_app(replace(settings, environment=Environment.PRODUCTION))
    container: Container = app.extensions["container"]
    container.session_factory = session_factory

    result = _seed(app)

    assert result.exit_code != 0
    assert "Refusing to seed initial data because FLASK_ENV is 'production'" in result.output
    assert set(_counts(db_session).values()) == {0}


def test_invalid_configuration_fails_without_changes(
    db_app: Flask, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SEED_ORGANIZER_PASSWORD", "short")

    result = _seed(db_app)

    assert result.exit_code != 0
    assert "Invalid seed configuration: SEED_ORGANIZER_PASSWORD" in result.output
    assert set(_counts(db_session).values()) == {0}


def test_unexpected_failure_is_reported_and_rolled_back(
    db_app: Flask, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    build_use_case = RequestScope.seed_initial_data

    def failing_use_case(scope: RequestScope) -> SeedInitialDataUseCase:
        use_case = build_use_case(scope)
        monkeypatch.setattr(use_case, "_sessions", _FailingSessions())
        return use_case

    monkeypatch.setattr(RequestScope, "seed_initial_data", failing_use_case)

    result = _seed(db_app)

    assert result.exit_code != 0
    assert "Initial data seeding failed unexpectedly. No changes were saved" in result.output
    assert set(_counts(db_session).values()) == {0}


class _FailingSessions:
    def get_by_id(self, _session_id: int) -> None:
        return None

    def add(self, *_: object) -> None:
        raise RuntimeError("simulated database failure")
