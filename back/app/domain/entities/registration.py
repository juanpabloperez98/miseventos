from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True, kw_only=True)
class Registration:
    user_id: int
    event_id: int
    id: int | None = None
    registered_at: datetime | None = None
