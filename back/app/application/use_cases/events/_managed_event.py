from app.application.dto import Actor
from app.application.services import EventAccessPolicy
from app.domain.entities import Event
from app.domain.exceptions import NotFoundError
from app.domain.ports import EventRepository


def load_event_for_management(
    events: EventRepository, access_policy: EventAccessPolicy, actor: Actor, event_id: int
) -> Event:
    access_policy.ensure_can_manage_events(actor)
    event = events.get_by_id_for_update(event_id)
    if event is None:
        raise NotFoundError.for_entity("Event")
    access_policy.ensure_can_manage(actor, event)
    return event
