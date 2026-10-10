from app.domain.entities import Speaker
from app.domain.ports import SpeakerRepository
from app.domain.value_objects import Page, PageRequest


class ListSpeakersUseCase:
    def __init__(self, speakers: SpeakerRepository) -> None:
        self._speakers = speakers

    def execute(self, page: int = 1, per_page: int = 10) -> Page[Speaker]:
        return self._speakers.list_all(PageRequest(page, per_page))
