from dataclasses import dataclass
from datetime import datetime

from app.domain.entities import Session


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


@dataclass(frozen=True, slots=True)
class SessionView:
    """Read model returned by the session use cases: the session plus its speaker's name."""

    id: int | None
    event_id: int
    speaker_id: int | None
    speaker_name: str | None
    title: str
    description: str | None
    start_time: datetime
    end_time: datetime
    capacity: int
    created_at: datetime | None
    updated_at: datetime | None

    @classmethod
    def from_session(cls, session: Session, speaker_name: str | None = None) -> "SessionView":
        return cls(
            id=session.id,
            event_id=session.event_id,
            speaker_id=session.speaker_id,
            speaker_name=speaker_name,
            title=session.title,
            description=session.description,
            start_time=session.start_time,
            end_time=session.end_time,
            capacity=session.capacity,
            created_at=session.created_at,
            updated_at=session.updated_at,
        )
