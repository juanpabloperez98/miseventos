from dataclasses import dataclass
from datetime import datetime

from app.domain.exceptions import InvalidValueError


@dataclass(frozen=True, slots=True)
class TimeRange:
    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        if self.start.tzinfo is None or self.end.tzinfo is None:
            raise InvalidValueError("Dates must include timezone information")
        if self.start >= self.end:
            raise InvalidValueError("Start must be before end")

    def contains(self, other: "TimeRange") -> bool:
        return self.start <= other.start and other.end <= self.end
