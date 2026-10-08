from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class SessionDetails:
    title: str
    start_time: datetime
    end_time: datetime
    capacity: int
    description: str | None = None
    speaker_id: int | None = None


@dataclass(frozen=True, slots=True)
class CreateSessionCommand:
    event_id: int
    details: SessionDetails


@dataclass(frozen=True, slots=True)
class UpdateSessionCommand:
    session_id: int
    details: SessionDetails
