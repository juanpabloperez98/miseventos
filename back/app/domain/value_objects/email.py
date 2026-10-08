import re
from dataclasses import dataclass

from app.domain.exceptions import InvalidValueError

_EMAIL_PATTERN = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")


@dataclass(frozen=True, slots=True)
class Email:
    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip().lower()
        if not _EMAIL_PATTERN.fullmatch(normalized):
            raise InvalidValueError("Invalid email address")
        object.__setattr__(self, "value", normalized)

    def __str__(self) -> str:
        return self.value
