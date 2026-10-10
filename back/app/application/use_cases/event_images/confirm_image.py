import logging

from app.application.dto import Actor, ConfirmImageCommand
from app.application.services import EventAccessPolicy, EventImagePolicy
from app.application.use_cases.event_images._shared import discard_image, load_editable_event
from app.application.use_cases.events._managed_event import load_event_for_management
from app.domain.entities import EventImage
from app.domain.exceptions import InvalidValueError
from app.domain.ports import EventImageRepository, EventRepository, ImageStorage, UnitOfWork

logger = logging.getLogger(__name__)


class ConfirmEventImageUseCase:
    """Makes an uploaded image the cover of the event, after verifying it with the image service.

    1. Permissions and the public id (it must be one issued for this event) are checked.
    2. The read transaction is closed before calling the image service, so no row stays locked
       during the network call.
    3. The metadata stored by the image service (not the client's) is validated.
    4. The event is locked and checked again, and the image is saved and committed.
    5. Only then is the previous cover deleted from the image service.

    If saving fails, the new upload is deleted (compensation) and the previous cover is kept.
    """

    def __init__(
        self,
        events: EventRepository,
        images: EventImageRepository,
        access_policy: EventAccessPolicy,
        storage: ImageStorage,
        policy: EventImagePolicy,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._events = events
        self._images = images
        self._access_policy = access_policy
        self._storage = storage
        self._policy = policy
        self._unit_of_work = unit_of_work

    def execute(self, actor: Actor, command: ConfirmImageCommand) -> EventImage:
        event_id, public_id = command.event_id, command.public_id
        load_editable_event(self._events, self._access_policy, actor, event_id)
        if not self._policy.belongs_to_event(public_id, event_id):
            raise InvalidValueError("The image was not uploaded for this event")

        current = self._images.get_by_event(event_id)
        if current is not None and current.public_id == public_id:
            return current  # Already confirmed (e.g. a retried request).
        self._unit_of_work.rollback()

        stored = self._storage.get_image(public_id)
        if stored is None or stored.public_id != public_id:
            raise InvalidValueError("The uploaded image could not be verified")
        try:
            self._policy.ensure_acceptable(stored)
        except InvalidValueError:
            discard_image(self._storage, public_id, "rejected_upload")
            raise

        try:
            load_event_for_management(self._events, self._access_policy, actor, event_id)
            previous = self._images.get_by_event(event_id)
            if previous is not None and previous.public_id == public_id:
                self._unit_of_work.rollback()
                return previous  # Confirmed concurrently by another request.
            saved = self._images.save(
                EventImage(
                    event_id=event_id,
                    public_id=stored.public_id,
                    secure_url=stored.secure_url,
                    width=stored.width,
                    height=stored.height,
                    format=stored.format,
                    bytes=stored.bytes,
                )
            )
            self._unit_of_work.commit()
        except Exception:
            self._unit_of_work.rollback()
            discard_image(self._storage, public_id, "confirmation_failed")
            raise

        if previous is not None:
            discard_image(self._storage, previous.public_id, "replaced")
        logger.info("event_image_confirmed", extra={"event_id": event_id, "user_id": actor.user_id})
        return saved
