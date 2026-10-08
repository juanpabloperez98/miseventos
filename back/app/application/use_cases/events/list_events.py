from app.application.dto import ListEventsQuery
from app.domain.entities import Event
from app.domain.enums import EventStatus
from app.domain.ports import EventRepository, EventSearchCriteria
from app.domain.value_objects import Page, PageRequest


class ListPublishedEventsUseCase:
    def __init__(self, events: EventRepository) -> None:
        self._events = events

    def execute(self, query: ListEventsQuery) -> Page[Event]:
        criteria = EventSearchCriteria(
            text=(query.search or "").strip() or None,
            status=EventStatus.PUBLISHED,
        )
        return self._events.search(criteria, PageRequest(query.page, query.per_page))
