from dataclasses import dataclass
from datetime import datetime

from app.domain.entities._validation import require_positive, require_text


@dataclass(slots=True, kw_only=True)
class EventImage:
    """Cover image of an event, stored in the image service (an event has at most one)."""

    event_id: int
    public_id: str
    secure_url: str
    width: int
    height: int
    format: str
    bytes: int
    id: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        self.public_id = require_text(self.public_id, "public_id")
        self.secure_url = require_text(self.secure_url, "secure_url")
        self.format = require_text(self.format, "format").lower()
        self.width = require_positive(self.width, "width")
        self.height = require_positive(self.height, "height")
        self.bytes = require_positive(self.bytes, "bytes")
