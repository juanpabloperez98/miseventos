from app.application.dto import Actor
from app.domain.entities import Event
from app.domain.ports import EventRepository


class ListMyRegisteredEventsUseCase:
    def __init__(self, events: EventRepository) -> None:
        self._events = events

    def execute(self, actor: Actor) -> list[Event]:
        return self._events.list_by_attendee(actor.user_id)
