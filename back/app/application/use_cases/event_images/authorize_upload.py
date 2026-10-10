import logging

from app.application.dto import Actor, ImageUploadRequest
from app.application.services import EventAccessPolicy, EventImagePolicy
from app.application.use_cases.event_images._shared import load_editable_event
from app.domain.ports import EventRepository, ImageStorage, SignedImageUpload

logger = logging.getLogger(__name__)


class AuthorizeEventImageUploadUseCase:
    """Signs a direct upload from the browser to the image service. The file never reaches us."""

    def __init__(
        self,
        events: EventRepository,
        access_policy: EventAccessPolicy,
        storage: ImageStorage,
        policy: EventImagePolicy,
    ) -> None:
        self._events = events
        self._access_policy = access_policy
        self._storage = storage
        self._policy = policy

    def execute(self, actor: Actor, request: ImageUploadRequest) -> SignedImageUpload:
        load_editable_event(self._events, self._access_policy, actor, request.event_id)
        self._policy.ensure_valid_upload(request.filename, request.content_type, request.size)

        # The public id and formats come from the server: the signature only covers them.
        public_id = self._policy.new_public_id(request.event_id)
        upload = self._storage.sign_upload(public_id, self._policy.allowed_formats)
        logger.info(
            "event_image_upload_authorized",
            extra={"event_id": request.event_id, "user_id": actor.user_id},
        )
        return upload
