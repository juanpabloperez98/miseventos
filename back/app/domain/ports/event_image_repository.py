from abc import ABC, abstractmethod

from app.domain.entities import EventImage


class EventImageRepository(ABC):
    @abstractmethod
    def get_by_event(self, event_id: int) -> EventImage | None: ...

    @abstractmethod
    def save(self, image: EventImage) -> EventImage:
        """Store the image as the cover of its event, replacing the previous one if any."""

    @abstractmethod
    def delete_by_event(self, event_id: int) -> None: ...
