from app.application.dto import Actor, ListEventsQuery
from app.application.services import EventAccessPolicy
from app.domain.entities import Event
from app.domain.ports import EventRepository, EventSearchCriteria
from app.domain.value_objects import Page, PageRequest


class ListEventsUseCase:
    def __init__(self, events: EventRepository, access_policy: EventAccessPolicy) -> None:
        self._events = events
        self._access_policy = access_policy

    def execute(self, query: ListEventsQuery, actor: Actor | None = None) -> Page[Event]:
        criteria = EventSearchCriteria(
            visibility=self._access_policy.visibility_for(actor),
            name=(query.search or "").strip() or None,
            status=query.status,
        )
        return self._events.search(criteria, PageRequest(query.page, query.per_page))
