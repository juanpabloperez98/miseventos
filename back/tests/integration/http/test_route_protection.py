from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from flask import Flask
from flask.testing import FlaskClient
from sqlalchemy.orm import Session

from app.container import Container
from app.domain.enums import UserRole
from app.infrastructure.database.models import UserModel
from app.infrastructure.database.repositories import SqlAlchemyUserRepository
from app.infrastructure.security import JwtTokenService, Sha256PasswordHasher
from tests.conftest import TEST_JWT_SECRET
from tests.factories import build_user

PASSWORD = "correct-horse-battery"
EVENT = {
    "name": "Python Conference",
    "location": "Bogota",
    "start_date": "2030-05-10T10:00:00+00:00",
    "end_date": "2030-05-10T18:00:00+00:00",
    "capacity": 100,
}


def _register_and_login(client: FlaskClient, email: str) -> tuple[int, str]:
    registration = client.post(
        "/api/auth/register", json={"name": "User", "email": email, "password": PASSWORD}
    )
    assert registration.status_code == 201, registration.get_json()
    login = client.post("/api/auth/login", json={"email": email, "password": PASSWORD})
    assert login.status_code == 200, login.get_json()
    user_id: int = registration.get_json()["id"]
    token: str = login.get_json()["access_token"]
    return user_id, token


def _login_seeded_user(
    client: FlaskClient, db_session: Session, email: str, role: UserRole
) -> tuple[int, str]:
    user = SqlAlchemyUserRepository(db_session).add(
        build_user(email=email, role=role, password_hash=Sha256PasswordHasher().hash(PASSWORD))
    )
    db_session.commit()
    login = client.post("/api/auth/login", json={"email": email, "password": PASSWORD})
    assert login.status_code == 200
    assert user.id is not None
    token: str = login.get_json()["access_token"]
    return user.id, token


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _expired_token(user_id: int, role: UserRole) -> str:
    issued_long_ago = datetime.now(UTC) - timedelta(hours=2)
    service = JwtTokenService(TEST_JWT_SECRET, timedelta(minutes=5), clock=lambda: issued_long_ago)
    return service.issue(user_id, role).value


def _forged_token(user_id: int, role: UserRole) -> str:
    service = JwtTokenService("another-secret-key-with-at-least-32-characters", timedelta(hours=1))
    return service.issue(user_id, role).value


@pytest.fixture
def organizer(db_client: FlaskClient, db_session: Session) -> tuple[int, str]:
    return _login_seeded_user(db_client, db_session, "organizer@example.com", UserRole.ORGANIZER)


@pytest.fixture
def event_id(db_client: FlaskClient, organizer: tuple[int, str]) -> int:
    response = db_client.post("/api/events", json=EVENT, headers=_bearer(organizer[1]))
    assert response.status_code == 201
    created_id: int = response.get_json()["id"]
    return created_id


class TestRegisterLoginAndManageEvents:
    def test_full_flow_with_a_token_obtained_by_login(
        self, db_client: FlaskClient, db_session: Session
    ) -> None:
        user_id, token = _login_seeded_user(
            db_client, db_session, "flow@example.com", UserRole.ORGANIZER
        )

        created = db_client.post("/api/events", json=EVENT, headers=_bearer(token))
        updated = db_client.put(
            f"/api/events/{created.get_json()['id']}",
            json={**EVENT, "name": "Python Summit", "status": "PUBLISHED"},
            headers=_bearer(token),
        )

        assert created.status_code == 201
        assert created.get_json()["created_by"] == user_id
        assert updated.status_code == 200
        assert (updated.get_json()["name"], updated.get_json()["status"]) == (
            "Python Summit",
            "PUBLISHED",
        )

    def test_publicly_registered_user_is_authenticated_but_not_authorized(
        self, db_client: FlaskClient, event_id: int
    ) -> None:
        _, token = _register_and_login(db_client, "new.user@example.com")

        me = db_client.get("/api/auth/me", headers=_bearer(token))
        create = db_client.post("/api/events", json=EVENT, headers=_bearer(token))
        update = db_client.put(f"/api/events/{event_id}", json=EVENT, headers=_bearer(token))

        assert (me.status_code, me.get_json()["role"]) == (200, "ATTENDEE")
        assert create.status_code == 403
        assert update.status_code == 403

    def test_owner_is_taken_from_the_token_not_the_payload(
        self, db_client: FlaskClient, organizer: tuple[int, str]
    ) -> None:
        response = db_client.post(
            "/api/events", json={**EVENT, "created_by": 999}, headers=_bearer(organizer[1])
        )

        assert response.status_code == 422
        assert response.get_json()["errors"]["json"]["created_by"] == ["Unknown field."]

    def test_token_of_a_deleted_user_is_rejected(
        self, db_client: FlaskClient, db_session: Session
    ) -> None:
        user_id, token = _register_and_login(db_client, "ghost@example.com")
        db_session.delete(db_session.get(UserModel, user_id))
        db_session.commit()

        response = db_client.post("/api/events", json=EVENT, headers=_bearer(token))

        assert response.status_code == 401
        assert response.get_json() == {"message": "Invalid or expired token"}


def _protected_requests(event_id: int) -> list[tuple[str, str, dict[str, Any]]]:
    return [
        ("POST", "/api/events", EVENT),
        ("PUT", f"/api/events/{event_id}", EVENT),
    ]


class TestAuthenticationBeforeAuthorization:
    @pytest.mark.parametrize(
        "method_index", [0, 1], ids=["POST /api/events", "PUT /api/events/{id}"]
    )
    @pytest.mark.parametrize(
        ("headers_factory", "message"),
        [
            (lambda _user: {}, "Missing bearer token"),
            (
                lambda _user: {"Authorization": "Token abc"},
                "Authorization header must use the Bearer scheme",
            ),
            (lambda _user: {"Authorization": "Bearer not-a-jwt"}, "Invalid or expired token"),
            (lambda user: _bearer(_forged_token(user, UserRole.ADMIN)), "Invalid or expired token"),
            (lambda user: _bearer(_expired_token(user, UserRole.ORGANIZER)), "Token has expired"),
        ],
        ids=["missing", "wrong_scheme", "malformed", "forged_admin", "expired"],
    )
    def test_unauthenticated_requests_get_401(
        self,
        db_client: FlaskClient,
        organizer: tuple[int, str],
        event_id: int,
        method_index: int,
        headers_factory: Any,
        message: str,
    ) -> None:
        method, url, payload = _protected_requests(event_id)[method_index]

        response = db_client.open(
            url, method=method, json=payload, headers=headers_factory(organizer[0])
        )

        assert response.status_code == 401
        assert response.get_json() == {"message": message}
        assert response.headers["WWW-Authenticate"] == "Bearer"

    @pytest.mark.parametrize(
        "method_index", [0, 1], ids=["POST /api/events", "PUT /api/events/{id}"]
    )
    def test_authenticated_attendee_gets_403(
        self,
        db_client: FlaskClient,
        db_session: Session,
        event_id: int,
        method_index: int,
    ) -> None:
        _, token = _login_seeded_user(db_client, db_session, "att@example.com", UserRole.ATTENDEE)
        method, url, payload = _protected_requests(event_id)[method_index]

        response = db_client.open(url, method=method, json=payload, headers=_bearer(token))

        assert response.status_code == 403

    def test_authenticated_organizer_cannot_update_a_foreign_event(
        self, db_client: FlaskClient, db_session: Session, event_id: int
    ) -> None:
        _, token = _login_seeded_user(
            db_client, db_session, "other@example.com", UserRole.ORGANIZER
        )

        response = db_client.put(f"/api/events/{event_id}", json=EVENT, headers=_bearer(token))

        assert response.status_code == 403
        assert response.get_json() == {"message": "You can only manage your own events"}

    def test_valid_token_reaches_validation(
        self, db_client: FlaskClient, organizer: tuple[int, str]
    ) -> None:
        response = db_client.post(
            "/api/events", json={**EVENT, "capacity": 0}, headers=_bearer(organizer[1])
        )

        assert response.status_code == 422

    def test_role_comes_from_the_database_not_the_token_claim(
        self, db_client: FlaskClient, db_app: Flask, db_session: Session
    ) -> None:
        attendee_id, _ = _login_seeded_user(
            db_client, db_session, "claims@example.com", UserRole.ATTENDEE
        )
        container: Container = db_app.extensions["container"]
        admin_claim_token = container.token_service.issue(attendee_id, UserRole.ADMIN).value

        response = db_client.post("/api/events", json=EVENT, headers=_bearer(admin_claim_token))

        assert response.status_code == 403

    def test_public_routes_stay_public(self, db_client: FlaskClient, event_id: int) -> None:
        assert db_client.get("/api/events").status_code == 200
        assert db_client.get("/health").status_code == 200
        assert db_client.get(f"/api/events/{event_id}").status_code == 404
