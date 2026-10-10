from app.application.dto import Actor
from app.application.services import EventAccessPolicy
from app.application.use_cases.event_images._shared import discard_image
from app.application.use_cases.events._managed_event import load_event_for_management
from app.domain.exceptions import NotFoundError
from app.domain.ports import EventImageRepository, EventRepository, ImageStorage, UnitOfWork


class DeleteEventImageUseCase:
    """Removes the cover of an event: first from the database, then from the image service."""

    def __init__(
        self,
        events: EventRepository,
        images: EventImageRepository,
        access_policy: EventAccessPolicy,
        storage: ImageStorage,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._events = events
        self._images = images
        self._access_policy = access_policy
        self._storage = storage
        self._unit_of_work = unit_of_work

    def execute(self, actor: Actor, event_id: int) -> None:
        event = load_event_for_management(self._events, self._access_policy, actor, event_id)
        event.ensure_editable()
        image = self._images.get_by_event(event_id)
        if image is None:
            raise NotFoundError.for_entity("Event image")
        self._images.delete_by_event(event_id)
        self._unit_of_work.commit()
        discard_image(self._storage, image.public_id, "removed")
