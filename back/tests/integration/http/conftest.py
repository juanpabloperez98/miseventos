from collections.abc import Callable
from dataclasses import dataclass

import pytest
from flask import Flask
from sqlalchemy.orm import Session

from app.container import Container
from app.domain.enums import UserRole
from app.infrastructure.database.repositories import SqlAlchemyUserRepository
from tests.factories import build_user


@dataclass(frozen=True)
class ApiUser:
    id: int
    headers: dict[str, str]


UserFactory = Callable[[UserRole, str], ApiUser]


@pytest.fixture
def make_api_user(db_app: Flask, db_session: Session) -> UserFactory:
    container: Container = db_app.extensions["container"]

    def factory(role: UserRole, email: str) -> ApiUser:
        user = SqlAlchemyUserRepository(db_session).add(build_user(email=email, role=role))
        db_session.commit()
        assert user.id is not None
        token = container.token_service.issue(user.id, role).value
        return ApiUser(id=user.id, headers={"Authorization": f"Bearer {token}"})

    return factory


@pytest.fixture
def admin(make_api_user: UserFactory) -> ApiUser:
    return make_api_user(UserRole.ADMIN, "admin@example.com")


@pytest.fixture
def organizer(make_api_user: UserFactory) -> ApiUser:
    return make_api_user(UserRole.ORGANIZER, "organizer@example.com")


@pytest.fixture
def other_organizer(make_api_user: UserFactory) -> ApiUser:
    return make_api_user(UserRole.ORGANIZER, "other.organizer@example.com")


@pytest.fixture
def attendee(make_api_user: UserFactory) -> ApiUser:
    return make_api_user(UserRole.ATTENDEE, "attendee@example.com")
