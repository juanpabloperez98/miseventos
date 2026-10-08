from typing import Any

import pytest
from flask import Blueprint, Flask
from flask.testing import FlaskClient
from sqlalchemy.orm import Session

from app.adapters.http.middleware import authenticated, require_permission
from app.domain.enums import Permission, UserRole
from app.infrastructure.database.repositories import SqlAlchemyUserRepository
from app.infrastructure.security import Sha256PasswordHasher
from tests.factories import build_user

PASSWORD = "correct-horse-battery"
REGISTRATION = {"name": "Ada Lovelace", "email": "Ada@Example.com", "password": PASSWORD}


def _register(client: FlaskClient, **overrides: Any) -> Any:
    return client.post("/api/auth/register", json={**REGISTRATION, **overrides})


def _login(client: FlaskClient, email: str = "ada@example.com", password: str = PASSWORD) -> Any:
    return client.post("/api/auth/login", json={"email": email, "password": password})


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


class TestRegister:
    def test_creates_attendee_without_exposing_password(self, db_client: FlaskClient) -> None:
        response = _register(db_client)
        body = response.get_json()

        assert response.status_code == 201
        assert body["email"] == "ada@example.com"
        assert body["role"] == "ATTENDEE"
        assert "password" not in body
        assert "password_hash" not in body
        assert body["created_at"] is not None

    def test_rejects_duplicate_email(self, db_client: FlaskClient) -> None:
        _register(db_client)

        response = _register(db_client, email="ADA@example.com")

        assert response.status_code == 409
        assert response.get_json() == {"message": "Email is already registered"}

    def test_rejects_invalid_payload_with_field_errors(self, db_client: FlaskClient) -> None:
        response = _register(db_client, email="not-an-email", password="short")
        body = response.get_json()

        assert response.status_code == 422
        assert body["message"] == "Request validation failed"
        assert set(body["errors"]["json"]) == {"email", "password"}


class TestLogin:
    def test_returns_bearer_token(self, db_client: FlaskClient) -> None:
        _register(db_client)

        response = _login(db_client)
        body = response.get_json()

        assert response.status_code == 200
        assert body["token_type"] == "Bearer"
        assert body["access_token"]
        assert body["expires_at"]

    def test_rejects_wrong_password(self, db_client: FlaskClient) -> None:
        _register(db_client)

        response = _login(db_client, password="wrong-password")

        assert response.status_code == 401
        assert response.get_json() == {"message": "Invalid email or password"}
        assert response.headers["WWW-Authenticate"] == "Bearer"


class TestMe:
    def test_returns_authenticated_user(self, db_client: FlaskClient) -> None:
        _register(db_client)
        token = _login(db_client).get_json()["access_token"]

        response = db_client.get("/api/auth/me", headers=_bearer(token))

        assert response.status_code == 200
        assert response.get_json()["email"] == "ada@example.com"

    @pytest.mark.parametrize(
        ("headers", "message"),
        [
            ({}, "Missing bearer token"),
            ({"Authorization": "Basic abc"}, "Authorization header must use the Bearer scheme"),
            ({"Authorization": "Bearer "}, "Missing bearer token"),
            ({"Authorization": "Bearer not-a-jwt"}, "Invalid or expired token"),
        ],
    )
    def test_rejects_missing_or_invalid_credentials(
        self, db_client: FlaskClient, headers: dict[str, str], message: str
    ) -> None:
        response = db_client.get("/api/auth/me", headers=headers)

        assert response.status_code == 401
        assert response.get_json() == {"message": message}


class TestRoleBasedAuthorization:
    @pytest.fixture
    def protected_client(self, db_app: Flask) -> FlaskClient:
        blueprint = Blueprint("rbac_probe", __name__)

        @blueprint.get("/rbac-probe")
        @authenticated
        @require_permission(Permission.MANAGE_EVENTS)
        def probe() -> dict[str, str]:
            return {"status": "allowed"}

        db_app.register_blueprint(blueprint)
        return db_app.test_client()

    def _token_for(self, client: FlaskClient, db_session: Session, role: UserRole) -> str:
        email = f"{role.value.lower()}@example.com"
        SqlAlchemyUserRepository(db_session).add(
            build_user(email=email, role=role, password_hash=Sha256PasswordHasher().hash(PASSWORD))
        )
        db_session.commit()
        token: str = _login(client, email=email).get_json()["access_token"]
        return token

    @pytest.mark.parametrize(
        ("role", "expected_status"),
        [(UserRole.ADMIN, 200), (UserRole.ORGANIZER, 200), (UserRole.ATTENDEE, 403)],
    )
    def test_permission_is_checked_against_role(
        self,
        protected_client: FlaskClient,
        db_session: Session,
        role: UserRole,
        expected_status: int,
    ) -> None:
        token = self._token_for(protected_client, db_session, role)

        response = protected_client.get("/rbac-probe", headers=_bearer(token))

        assert response.status_code == expected_status

    def test_authentication_runs_before_authorization(self, protected_client: FlaskClient) -> None:
        assert protected_client.get("/rbac-probe").status_code == 401
