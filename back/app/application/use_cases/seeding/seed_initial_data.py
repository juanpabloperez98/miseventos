import logging
from collections.abc import Callable
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from typing import Protocol

from app.application.dto import SeedInitialDataCommand, SeedReport, SeedUser
from app.application.use_cases.seeding.catalog import (
    DEFAULT_CATALOG,
    EVENT_START_TIME,
    EventSeed,
    SeedCatalog,
    SessionSeed,
    SpeakerSeed,
)
from app.domain.entities import Event, Session, Speaker, User
from app.domain.enums import UserRole
from app.domain.exceptions import InvalidValueError
from app.domain.ports import (
    EventRepository,
    PasswordHasher,
    SeedEntityType,
    SeedRecord,
    SeedRecordRepository,
    SessionRepository,
    SpeakerRepository,
    UnitOfWork,
    UserRepository,
)
from app.domain.value_objects import Email

logger = logging.getLogger(__name__)


class _Persisted(Protocol):
    id: int | None


def _utc_now() -> datetime:
    return datetime.now(UTC)


class SeedInitialDataUseCase:
    """Creates the missing seed users and demo data without touching existing rows.

    Users are identified by their configured email. Speakers, events and sessions are tracked
    in ``seed_records`` by a stable key, so manual edits are kept and only rows whose entity no
    longer exists are created again.
    """

    def __init__(
        self,
        users: UserRepository,
        speakers: SpeakerRepository,
        events: EventRepository,
        sessions: SessionRepository,
        seed_records: SeedRecordRepository,
        password_hasher: PasswordHasher,
        unit_of_work: UnitOfWork,
        catalog: SeedCatalog = DEFAULT_CATALOG,
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        self._users = users
        self._speakers = speakers
        self._events = events
        self._sessions = sessions
        self._seed_records = seed_records
        self._password_hasher = password_hasher
        self._unit_of_work = unit_of_work
        self._catalog = catalog
        self._clock = clock

    def execute(self, command: SeedInitialDataCommand) -> SeedReport:
        if command.demo_data and command.organizer is None:
            raise InvalidValueError("Demo data requires an enabled seed ORGANIZER user")

        report = SeedReport()
        try:
            users = {seed.role: self._ensure_user(seed, report) for seed in command.users}
            if command.demo_data:
                self._seed_demo_data(users[UserRole.ORGANIZER], report)
            self._unit_of_work.commit()
        except Exception:
            self._unit_of_work.rollback()
            raise

        logger.info("initial_data_seeded", extra=asdict(report))
        return report

    def _ensure_user(self, seed: SeedUser, report: SeedReport) -> User:
        email = Email(seed.email).value
        existing = self._users.get_by_email(email)
        if existing is not None:
            report.users_existing += 1
            if existing.role is not seed.role:
                logger.warning(
                    "seed_user_role_mismatch",
                    extra={
                        "user_id": existing.id,
                        "expected_role": seed.role.value,
                        "actual_role": existing.role.value,
                    },
                )
            return existing

        user = self._users.add(
            User(
                name=seed.name,
                email=email,
                password_hash=self._password_hasher.hash(seed.password),
                role=seed.role,
            )
        )
        report.users_created += 1
        logger.info("seed_user_created", extra={"user_id": user.id, "role": user.role.value})
        return user

    def _seed_demo_data(self, organizer: User, report: SeedReport) -> None:
        if organizer.role is not UserRole.ORGANIZER or organizer.id is None:
            logger.warning(
                "seed_demo_data_skipped",
                extra={"reason": "organizer_role_mismatch", "user_id": organizer.id},
            )
            report.demo_data_skipped = True
            return

        today = self._clock().astimezone(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        speakers = {seed.key: self._ensure_speaker(seed, report) for seed in self._catalog.speakers}
        events = {
            seed.key: self._ensure_event(seed, organizer.id, today, report)
            for seed in self._catalog.events
        }
        for seed in self._catalog.sessions:
            speaker = speakers.get(seed.speaker_key) if seed.speaker_key else None
            self._ensure_session(seed, events[seed.event_key], speaker, report)

    def _ensure_speaker(self, seed: SpeakerSeed, report: SeedReport) -> Speaker:
        existing = self._find_seeded(seed.key, self._speakers.get_by_id, report)
        if existing is not None:
            return existing
        speaker = self._speakers.add(Speaker(name=seed.name, email=seed.email, bio=seed.bio))
        self._remember(seed.key, SeedEntityType.SPEAKER, speaker, report)
        return speaker

    def _ensure_event(
        self, seed: EventSeed, organizer_id: int, today: datetime, report: SeedReport
    ) -> Event:
        existing = self._find_seeded(seed.key, self._events.get_by_id, report)
        if existing is not None:
            return existing

        start_date = today + timedelta(days=seed.days_from_today) + EVENT_START_TIME
        event = Event(
            name=seed.name,
            description=seed.description,
            location=seed.location,
            start_date=start_date,
            end_date=start_date + seed.duration,
            capacity=seed.capacity,
            created_by=organizer_id,
        )
        for status in seed.status_path:
            event = event.with_status(status)

        created = self._events.add(event)
        self._remember(seed.key, SeedEntityType.EVENT, created, report)
        return created

    def _ensure_session(
        self, seed: SessionSeed, event: Event, speaker: Speaker | None, report: SeedReport
    ) -> None:
        if self._find_seeded(seed.key, self._sessions.get_by_id, report) is not None:
            return
        if event.id is None:
            raise ValueError("Seed sessions require a persisted event")

        start_time = event.start_date + seed.offset_from_event_start
        session = Session(
            event_id=event.id,
            speaker_id=speaker.id if speaker else None,
            title=seed.title,
            description=seed.description,
            start_time=start_time,
            end_time=start_time + seed.duration,
            capacity=seed.capacity,
        )
        try:
            session.ensure_fits_within(event)
        except InvalidValueError:
            # The event schedule or capacity was edited manually; never change the event to fit
            # seed data.
            logger.warning(
                "seed_session_skipped",
                extra={
                    "seed_key": seed.key,
                    "event_id": event.id,
                    "reason": "outside_event_schedule",
                },
            )
            report.records_skipped += 1
            return

        self._remember(seed.key, SeedEntityType.SESSION, self._sessions.add(session), report)

    def _find_seeded[T](
        self, seed_key: str, find: Callable[[int], T | None], report: SeedReport
    ) -> T | None:
        record = self._seed_records.get(seed_key)
        if record is None:
            return None
        existing = find(record.entity_id)
        if existing is not None:
            report.records_existing += 1
        return existing

    def _remember(
        self, seed_key: str, entity_type: SeedEntityType, entity: _Persisted, report: SeedReport
    ) -> None:
        if entity.id is None:
            raise ValueError(f"Seed {entity_type.value} was not persisted")
        self._seed_records.save(SeedRecord(seed_key, entity_type, entity.id))
        report.records_created += 1
        logger.info(
            "seed_record_created",
            extra={"seed_key": seed_key, "entity_type": entity_type.value, "entity_id": entity.id},
        )
