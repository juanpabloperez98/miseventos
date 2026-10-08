import threading
import uuid
from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass, field

import pytest
from sqlalchemy import Engine, delete, func, select

from app.application.dto import Actor
from app.application.services import AuthorizationService, EventAccessPolicy
from app.application.use_cases.registrations import RegisterForEventUseCase
from app.domain.entities import Registration
from app.domain.enums import UserRole
from app.infrastructure.database.models import EventModel, RegistrationModel, UserModel
from app.infrastructure.database.repositories import (
    SqlAlchemyEventRepository,
    SqlAlchemyRegistrationRepository,
    SqlAlchemyUserRepository,
)
from app.infrastructure.database.session import create_session_factory
from app.infrastructure.database.unit_of_work import SqlAlchemyUnitOfWork
from tests.factories import build_event, build_user


@dataclass
class CommittedData:
    engine: Engine
    user_ids: list[int] = field(default_factory=list)
    event_ids: list[int] = field(default_factory=list)

    def create_users(self, count: int) -> list[int]:
        with create_session_factory(self.engine)() as session:
            users = SqlAlchemyUserRepository(session)
            created = [
                users.add(build_user(email=f"{uuid.uuid4().hex}@concurrency.test")).id
                for _ in range(count)
            ]
            session.commit()
        ids = [user_id for user_id in created if user_id is not None]
        self.user_ids.extend(ids)
        return ids

    def create_event(self, capacity: int, registered_user_ids: list[int]) -> int:
        owner_id = self.create_users(1)[0]
        with create_session_factory(self.engine)() as session:
            event = SqlAlchemyEventRepository(session).add(
                build_event(created_by=owner_id, capacity=capacity)
            )
            assert event.id is not None
            registrations = SqlAlchemyRegistrationRepository(session)
            for user_id in registered_user_ids:
                registrations.add(Registration(user_id=user_id, event_id=event.id))
            session.commit()
        self.event_ids.append(event.id)
        return event.id

    def registration_count(self, event_id: int) -> int:
        with self.engine.connect() as connection:
            statement = select(func.count()).where(RegistrationModel.event_id == event_id)
            return connection.scalar(statement) or 0

    def cleanup(self) -> None:
        with self.engine.begin() as connection:
            connection.execute(
                delete(RegistrationModel).where(RegistrationModel.event_id.in_(self.event_ids))
            )
            connection.execute(delete(EventModel).where(EventModel.id.in_(self.event_ids)))
            connection.execute(delete(UserModel).where(UserModel.id.in_(self.user_ids)))


@pytest.fixture
def committed(engine: Engine) -> Iterator[CommittedData]:
    data = CommittedData(engine)
    yield data
    data.cleanup()


def _register_concurrently(engine: Engine, event_id: int, user_ids: list[int]) -> Counter[str]:
    session_factory = create_session_factory(engine)
    authorization = AuthorizationService()
    access_policy = EventAccessPolicy(authorization)
    barrier = threading.Barrier(len(user_ids))
    outcomes: Counter[str] = Counter()
    lock = threading.Lock()

    def attempt(user_id: int) -> None:
        with session_factory() as session:
            use_case = RegisterForEventUseCase(
                SqlAlchemyEventRepository(session),
                SqlAlchemyRegistrationRepository(session),
                authorization,
                access_policy,
                SqlAlchemyUnitOfWork(session),
            )
            barrier.wait()
            try:
                use_case.execute(Actor(user_id=user_id, role=UserRole.ATTENDEE), event_id)
                outcome = "registered"
            except Exception as error:
                outcome = type(error).__name__
        with lock:
            outcomes[outcome] += 1

    threads = [threading.Thread(target=attempt, args=(user_id,)) for user_id in user_ids]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)
    return outcomes


def test_two_requests_competing_for_the_last_seat(committed: CommittedData) -> None:
    event_id = committed.create_event(capacity=10, registered_user_ids=committed.create_users(9))

    outcomes = _register_concurrently(committed.engine, event_id, committed.create_users(2))

    assert outcomes == Counter({"registered": 1, "EventCapacityExceededError": 1})
    assert committed.registration_count(event_id) == 10


def test_capacity_is_never_exceeded_under_contention(committed: CommittedData) -> None:
    event_id = committed.create_event(capacity=5, registered_user_ids=[])

    outcomes = _register_concurrently(committed.engine, event_id, committed.create_users(12))

    assert outcomes == Counter({"registered": 5, "EventCapacityExceededError": 7})
    assert committed.registration_count(event_id) == 5


def test_same_user_registering_concurrently_is_stored_once(committed: CommittedData) -> None:
    event_id = committed.create_event(capacity=10, registered_user_ids=[])
    user_id = committed.create_users(1)[0]

    outcomes = _register_concurrently(committed.engine, event_id, [user_id] * 5)

    assert outcomes == Counter({"registered": 1, "AlreadyRegisteredToEventError": 4})
    assert committed.registration_count(event_id) == 1
