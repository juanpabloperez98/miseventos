import logging

from app.application.dto import Actor, EventRemovalResult
from app.application.services import EventAccessPolicy
from app.application.use_cases.events._managed_event import load_event_for_management
from app.domain.enums import EventRemoval, EventStatus
from app.domain.ports import EventRepository, UnitOfWork

logger = logging.getLogger(__name__)


class DeleteEventUseCase:
    def __init__(
        self, events: EventRepository, access_policy: EventAccessPolicy, unit_of_work: UnitOfWork
    ) -> None:
        self._events = events
        self._access_policy = access_policy
        self._unit_of_work = unit_of_work

    def execute(self, actor: Actor, event_id: int) -> EventRemovalResult:
        event = load_event_for_management(self._events, self._access_policy, actor, event_id)
        action = event.removal_action()

        if action is EventRemoval.DELETE:
            self._events.delete(event_id)
            result = EventRemovalResult(action=action)
        else:
            cancelled = self._events.update(event.with_status(EventStatus.CANCELLED))
            result = EventRemovalResult(action=action, event=cancelled)
        self._unit_of_work.commit()

        logger.info(
            "event_removed",
            extra={"event_id": event_id, "user_id": actor.user_id, "action": action.value},
        )
        return result
