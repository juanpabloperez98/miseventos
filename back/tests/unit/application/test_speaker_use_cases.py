from app.application.use_cases.speakers import ListSpeakersUseCase
from app.domain.entities import Speaker
from tests.unit.application.fakes import InMemorySpeakerRepository


def _repository_with(*names: str) -> InMemorySpeakerRepository:
    speakers = InMemorySpeakerRepository()
    for name in names:
        speakers.add(Speaker(name=name, email=f"{name.split()[0].lower()}@example.com"))
    return speakers


def test_lists_speakers_ordered_by_name() -> None:
    use_case = ListSpeakersUseCase(_repository_with("Grace Hopper", "Ada Lovelace"))

    page = use_case.execute()

    assert [speaker.name for speaker in page.items] == ["Ada Lovelace", "Grace Hopper"]
    assert page.total == 2


def test_paginates_speakers() -> None:
    use_case = ListSpeakersUseCase(_repository_with("Ada", "Barbara", "Carol"))

    page = use_case.execute(page=2, per_page=2)

    assert [speaker.name for speaker in page.items] == ["Carol"]
    assert (page.total, page.page, page.per_page) == (3, 2, 2)
