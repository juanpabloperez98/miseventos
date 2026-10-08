import hashlib
from typing import Any

import pytest
from flask import Blueprint, Flask
from flask.testing import FlaskClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.adapters.http.middleware import authenticated, require_permission
from app.domain.enums import Permission, UserRole
from app.infrastructure.database.models import UserModel
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

    def test_persists_user_with_salted_sha256_hash(
        self, db_client: FlaskClient, db_session: Session
    ) -> None:
        user_id = _register(db_client).get_json()["id"]

        stored = db_session.get(UserModel, user_id)

        assert stored is not None
        assert (stored.name, stored.email, stored.role) == (
            "Ada Lovelace",
            "ada@example.com",
            UserRole.ATTENDEE,
        )
        assert PASSWORD not in stored.password_hash
        salt, digest = stored.password_hash.split("$")
        assert digest == hashlib.sha256(f"{salt}{PASSWORD}".encode()).hexdigest()

    def test_same_password_gets_different_hashes(
        self, db_client: FlaskClient, db_session: Session
    ) -> None:
        first = _register(db_client, email="first@example.com").get_json()["id"]
        second = _register(db_client, email="second@example.com").get_json()["id"]

        hashes = db_session.scalars(
            select(UserModel.password_hash).where(UserModel.id.in_([first, second]))
        ).all()

        assert len(set(hashes)) == 2

    def test_duplicate_email_does_not_create_a_second_user(
        self, db_client: FlaskClient, db_session: Session
    ) -> None:
        _register(db_client)
        _register(db_client, email="ADA@EXAMPLE.COM", name="Impostor")

        count = db_session.scalar(select(func.count()).select_from(UserModel))

        assert count == 1

    @pytest.mark.parametrize(
        ("overrides", "field"),
        [
            ({"email": "ada@"}, "email"),
            ({"email": ""}, "email"),
            ({"email": "x" * 250 + "@example.com"}, "email"),
            ({"password": "1234567"}, "password"),
            ({"password": "x" * 129}, "password"),
            ({"password": None}, "password"),
            ({"name": ""}, "name"),
            ({"name": "x" * 121}, "name"),
        ],
    )
    def test_rejects_invalid_fields(
        self, db_client: FlaskClient, overrides: dict[str, Any], field: str
    ) -> None:
        response = _register(db_client, **overrides)

        assert response.status_code == 422
        assert field in response.get_json()["errors"]["json"]

    def test_rejects_missing_fields(self, db_client: FlaskClient) -> None:
        response = db_client.post("/api/auth/register", json={})

        assert response.status_code == 422
        assert set(response.get_json()["errors"]["json"]) == {"name", "email", "password"}

    def test_blank_name_is_rejected_by_the_domain(self, db_client: FlaskClient) -> None:
        response = _register(db_client, name="   ")

        assert response.status_code == 422
        assert response.get_json() == {"message": "name must not be blank"}

    @pytest.mark.parametrize(
        ("field", "value"),
        [
            ("role", "ADMIN"),
            ("role", "ORGANIZER"),
            ("id", 1),
            ("password_hash", "salt$digest"),
            ("created_at", "2030-01-01T00:00:00+00:00"),
            ("updated_at", "2030-01-01T00:00:00+00:00"),
        ],
    )
    def test_rejects_mass_assignment(
        self, db_client: FlaskClient, db_session: Session, field: str, value: Any
    ) -> None:
        response = _register(db_client, **{field: value})

        assert response.status_code == 422
        assert response.get_json()["errors"]["json"][field] == ["Unknown field."]
        assert db_session.scalar(select(func.count()).select_from(UserModel)) == 0

    def test_password_never_appears_in_responses(self, db_client: FlaskClient) -> None:
        responses = [
            _register(db_client),
            _register(db_client),
            _login(db_client),
            _login(db_client, password="wrong-password"),
        ]

        for response in responses:
            assert PASSWORD not in response.get_data(as_text=True)
            assert "password_hash" not in response.get_data(as_text=True)


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

    def test_unknown_email_gets_the_same_error_as_a_wrong_password(
        self, db_client: FlaskClient
    ) -> None:
        _register(db_client)

        unknown = _login(db_client, email="nobody@example.com")
        wrong_password = _login(db_client, password="wrong-password")

        assert unknown.status_code == wrong_password.status_code == 401
        assert (
            unknown.get_json()
            == wrong_password.get_json()
            == {"message": "Invalid email or password"}
        )

    def test_email_is_matched_case_insensitively(self, db_client: FlaskClient) -> None:
        _register(db_client)

        assert _login(db_client, email="  ADA@example.COM ").status_code == 200

    def test_password_is_case_sensitive(self, db_client: FlaskClient) -> None:
        _register(db_client)

        assert _login(db_client, password=PASSWORD.upper()).status_code == 401

    def test_token_identifies_the_user_and_role(
        self, db_client: FlaskClient, db_app: Flask
    ) -> None:
        user_id = _register(db_client).get_json()["id"]
        token = _login(db_client).get_json()["access_token"]

        claims = db_app.extensions["container"].token_service.decode(token)

        assert (claims.user_id, claims.role) == (user_id, UserRole.ATTENDEE)

    @pytest.mark.parametrize(
        "payload",
        [{}, {"email": "ada@example.com"}, {"password": PASSWORD}, {"email": "", "password": ""}],
    )
    def test_rejects_incomplete_payload(
        self, db_client: FlaskClient, payload: dict[str, str]
    ) -> None:
        assert db_client.post("/api/auth/login", json=payload).status_code == 422

    def test_rejects_unknown_fields(self, db_client: FlaskClient) -> None:
        _register(db_client)

        response = db_client.post(
            "/api/auth/login",
            json={"email": "ada@example.com", "password": PASSWORD, "role": "ADMIN"},
        )

        assert response.status_code == 422


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
