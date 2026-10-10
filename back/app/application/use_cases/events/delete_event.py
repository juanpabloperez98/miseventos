import logging

from app.application.dto import Actor, EventRemovalResult
from app.application.services import EventAccessPolicy
from app.application.use_cases.event_images._shared import discard_image
from app.application.use_cases.events._managed_event import load_event_for_management
from app.domain.enums import EventRemoval, EventStatus
from app.domain.ports import EventRepository, ImageStorage, UnitOfWork

logger = logging.getLogger(__name__)


class DeleteEventUseCase:
    """Deletes drafts and cancels published events.

    A deleted draft loses its cover image: the database row goes with the event (cascade) and the
    file is deleted from the image service after the commit. Cancelled events keep their image.
    """

    def __init__(
        self,
        events: EventRepository,
        access_policy: EventAccessPolicy,
        unit_of_work: UnitOfWork,
        storage: ImageStorage,
    ) -> None:
        self._events = events
        self._access_policy = access_policy
        self._unit_of_work = unit_of_work
        self._storage = storage

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

        if action is EventRemoval.DELETE and event.image is not None:
            discard_image(self._storage, event.image.public_id, "event_deleted")
        logger.info(
            "event_removed",
            extra={"event_id": event_id, "user_id": actor.user_id, "action": action.value},
        )
        return result
