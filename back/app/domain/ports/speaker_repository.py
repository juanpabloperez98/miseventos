from abc import ABC, abstractmethod

from app.domain.entities import Speaker
from app.domain.value_objects import Page, PageRequest


class SpeakerRepository(ABC):
    @abstractmethod
    def add(self, speaker: Speaker) -> Speaker: ...

    @abstractmethod
    def get_by_id(self, speaker_id: int) -> Speaker | None: ...

    @abstractmethod
    def update(self, speaker: Speaker) -> Speaker: ...

    @abstractmethod
    def delete(self, speaker_id: int) -> None: ...

    @abstractmethod
    def list_all(self, page: PageRequest) -> Page[Speaker]: ...
