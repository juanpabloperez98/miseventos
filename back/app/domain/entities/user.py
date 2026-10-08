from dataclasses import dataclass
from datetime import datetime

from app.domain.entities._validation import require_text
from app.domain.enums import UserRole
from app.domain.value_objects import Email


@dataclass(slots=True, kw_only=True)
class User:
    name: str
    email: str
    password_hash: str
    role: UserRole = UserRole.ATTENDEE
    id: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        self.name = require_text(self.name, "name")
        self.email = Email(self.email).value
