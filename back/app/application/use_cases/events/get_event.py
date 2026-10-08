from app.application.dto import Actor
from app.application.services import EventAccessPolicy
from app.domain.entities import Event
from app.domain.exceptions import NotFoundError
from app.domain.ports import EventRepository


class GetEventUseCase:
    def __init__(self, events: EventRepository, access_policy: EventAccessPolicy) -> None:
        self._events = events
        self._access_policy = access_policy

    def execute(self, event_id: int, actor: Actor | None = None) -> Event:
        event = self._events.get_by_id(event_id)
        if event is None or not self._access_policy.can_view(actor, event):
            raise NotFoundError.for_entity("Event")
        return event
