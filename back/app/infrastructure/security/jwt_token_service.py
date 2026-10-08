from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import jwt

from app.domain.enums import UserRole
from app.domain.exceptions import InvalidTokenError
from app.domain.ports import AccessToken, TokenClaims, TokenService

Clock = Callable[[], datetime]


def _utc_now() -> datetime:
    return datetime.now(UTC)


class JwtTokenService(TokenService):
    ALGORITHM = "HS256"

    def __init__(self, secret_key: str, expiration: timedelta, clock: Clock = _utc_now) -> None:
        self._secret_key = secret_key
        self._expiration = expiration
        self._clock = clock

    def issue(self, user_id: int, role: UserRole) -> AccessToken:
        issued_at = self._clock()
        expires_at = issued_at + self._expiration
        token = jwt.encode(
            {"sub": str(user_id), "role": role.value, "iat": issued_at, "exp": expires_at},
            self._secret_key,
            algorithm=self.ALGORITHM,
        )
        return AccessToken(value=token, expires_at=expires_at)

    def decode(self, token: str) -> TokenClaims:
        try:
            payload = jwt.decode(
                token,
                self._secret_key,
                algorithms=[self.ALGORITHM],
                options={"require": ["sub", "role", "iat", "exp"]},
            )
            return TokenClaims(
                user_id=int(payload["sub"]),
                role=UserRole(payload["role"]),
                expires_at=datetime.fromtimestamp(payload["exp"], UTC),
            )
        except jwt.ExpiredSignatureError as error:
            raise InvalidTokenError("Token has expired") from error
        except (jwt.InvalidTokenError, ValueError) as error:
            raise InvalidTokenError() from error
