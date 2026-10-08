from dataclasses import dataclass

from app.application.dto.user import UserDTO
from app.domain.enums import UserRole


@dataclass(frozen=True, slots=True)
class Actor:
    user_id: int
    role: UserRole

    @classmethod
    def from_user(cls, user: UserDTO) -> "Actor":
        return cls(user_id=user.id, role=user.role)
