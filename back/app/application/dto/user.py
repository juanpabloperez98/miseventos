from dataclasses import dataclass
from datetime import datetime

from app.domain.entities import User
from app.domain.enums import UserRole


@dataclass(frozen=True, slots=True)
class UserDTO:
    id: int
    name: str
    email: str
    role: UserRole
    created_at: datetime | None
    updated_at: datetime | None

    @classmethod
    def from_entity(cls, user: User) -> "UserDTO":
        if user.id is None:
            raise ValueError("Cannot build a UserDTO from a non persisted user")
        return cls(
            id=user.id,
            name=user.name,
            email=user.email,
            role=user.role,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )
