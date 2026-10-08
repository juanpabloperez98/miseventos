from dataclasses import dataclass
from datetime import datetime

from app.domain.entities._validation import optional_text, require_text
from app.domain.value_objects import Email


@dataclass(slots=True, kw_only=True)
class Speaker:
    name: str
    bio: str | None = None
    email: str | None = None
    id: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        self.name = require_text(self.name, "name")
        self.bio = optional_text(self.bio)
        email = optional_text(self.email)
        self.email = Email(email).value if email else None
