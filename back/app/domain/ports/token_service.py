from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

from app.domain.enums import UserRole


@dataclass(frozen=True, slots=True)
class AccessToken:
    value: str
    expires_at: datetime
    token_type: str = "Bearer"  # noqa: S105 - OAuth token type, not a credential


@dataclass(frozen=True, slots=True)
class TokenClaims:
    user_id: int
    role: UserRole
    expires_at: datetime


class TokenService(ABC):
    @abstractmethod
    def issue(self, user_id: int, role: UserRole) -> AccessToken: ...

    @abstractmethod
    def decode(self, token: str) -> TokenClaims: ...
