from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum


class SeedEntityType(StrEnum):
    SPEAKER = "speaker"
    EVENT = "event"
    SESSION = "session"


@dataclass(frozen=True, slots=True)
class SeedRecord:
    """Links a stable seed key to the database row created for it."""

    seed_key: str
    entity_type: SeedEntityType
    entity_id: int


class SeedRecordRepository(ABC):
    @abstractmethod
    def get(self, seed_key: str) -> SeedRecord | None: ...

    @abstractmethod
    def save(self, record: SeedRecord) -> None:
        """Insert the record or point an existing seed key to a new entity."""
