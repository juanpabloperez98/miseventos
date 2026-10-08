import logging

from app.application.dto import Actor, EventDetails
from app.application.services import EventAccessPolicy
from app.domain.entities import Event
from app.domain.enums import EventStatus
from app.domain.ports import EventRepository, UnitOfWork

logger = logging.getLogger(__name__)


class CreateEventUseCase:
    def __init__(
        self, events: EventRepository, access_policy: EventAccessPolicy, unit_of_work: UnitOfWork
    ) -> None:
        self._events = events
        self._access_policy = access_policy
        self._unit_of_work = unit_of_work

    def execute(self, actor: Actor, details: EventDetails) -> Event:
        self._access_policy.ensure_can_manage_events(actor)

        event = self._events.add(
            Event(
                name=details.name,
                description=details.description,
                location=details.location,
                start_date=details.start_date,
                end_date=details.end_date,
                capacity=details.capacity,
                created_by=actor.user_id,
                status=EventStatus.DRAFT,
            )
        )
        self._unit_of_work.commit()

        logger.info("event_created", extra={"event_id": event.id, "user_id": actor.user_id})
        return event
