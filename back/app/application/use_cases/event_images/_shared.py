import logging

from app.application.dto import Actor
from app.application.services import EventAccessPolicy
from app.domain.entities import Event
from app.domain.exceptions import ImageStorageError, NotFoundError
from app.domain.ports import EventRepository, ImageStorage

logger = logging.getLogger(__name__)


def load_editable_event(
    events: EventRepository, access_policy: EventAccessPolicy, actor: Actor, event_id: int
) -> Event:
    """Same checks as `load_event_for_management`, without locking the row (read only)."""
    access_policy.ensure_can_manage_events(actor)
    event = events.get_by_id(event_id)
    if event is None:
        raise NotFoundError.for_entity("Event")
    access_policy.ensure_can_manage(actor, event)
    event.ensure_editable()
    return event


def discard_image(storage: ImageStorage, public_id: str, reason: str) -> None:
    """Best-effort deletion of an image no longer referenced by the database.

    It runs after the database change is committed (or rolled back), so a failure here never
    leaves an event pointing to a missing image: at worst the image stays orphaned in the image
    service, and the log line identifies it for a manual cleanup.
    """
    try:
        storage.delete_image(public_id)
    except ImageStorageError:
        logger.warning(
            "event_image_cleanup_failed", extra={"public_id": public_id, "reason": reason}
        )
    else:
        logger.info("event_image_deleted", extra={"public_id": public_id, "reason": reason})
