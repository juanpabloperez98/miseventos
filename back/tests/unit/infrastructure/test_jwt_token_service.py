from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.domain.enums import UserRole
from app.domain.exceptions import InvalidTokenError
from app.infrastructure.security import JwtTokenService

SECRET = "unit-test-jwt-secret-key-with-at-least-32-chars"


def test_issued_token_round_trips_claims() -> None:
    service = JwtTokenService(SECRET, timedelta(minutes=30))

    token = service.issue(42, UserRole.ORGANIZER)
    claims = service.decode(token.value)

    assert token.token_type == "Bearer"
    assert claims.user_id == 42
    assert claims.role is UserRole.ORGANIZER
    assert claims.expires_at == token.expires_at.replace(microsecond=0)


def test_expiration_uses_configured_lifetime() -> None:
    now = datetime(2030, 1, 1, tzinfo=UTC)
    service = JwtTokenService(SECRET, timedelta(minutes=30), clock=lambda: now)

    assert service.issue(1, UserRole.ATTENDEE).expires_at == now + timedelta(minutes=30)


def test_rejects_expired_token() -> None:
    issued_long_ago = datetime.now(UTC) - timedelta(hours=2)
    service = JwtTokenService(SECRET, timedelta(minutes=30), clock=lambda: issued_long_ago)
    token = service.issue(1, UserRole.ATTENDEE)

    with pytest.raises(InvalidTokenError, match="expired"):
        JwtTokenService(SECRET, timedelta(minutes=30)).decode(token.value)


def test_rejects_token_signed_with_another_secret() -> None:
    token = JwtTokenService("another-secret-key-with-at-least-32-characters", timedelta(minutes=5))

    with pytest.raises(InvalidTokenError):
        JwtTokenService(SECRET, timedelta(minutes=5)).decode(token.issue(1, UserRole.ADMIN).value)


@pytest.mark.parametrize("token", ["", "not-a-jwt", "a.b.c"])
def test_rejects_malformed_tokens(token: str) -> None:
    with pytest.raises(InvalidTokenError):
        JwtTokenService(SECRET, timedelta(minutes=5)).decode(token)


def test_rejects_token_with_unknown_role() -> None:
    now = datetime.now(UTC)
    token = jwt.encode(
        {"sub": "1", "role": "SUPERUSER", "iat": now, "exp": now + timedelta(minutes=5)},
        SECRET,
        algorithm="HS256",
    )

    with pytest.raises(InvalidTokenError):
        JwtTokenService(SECRET, timedelta(minutes=5)).decode(token)


def test_rejects_unsigned_tokens() -> None:
    token = jwt.encode({"sub": "1", "role": "ADMIN"}, key=None, algorithm="none")

    with pytest.raises(InvalidTokenError):
        JwtTokenService(SECRET, timedelta(minutes=5)).decode(token)
