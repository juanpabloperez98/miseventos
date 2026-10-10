import re
from dataclasses import dataclass, field
from uuid import uuid4

from app.domain.exceptions import InvalidValueError
from app.domain.ports import StoredImage

DEFAULT_MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_FILENAME_LENGTH = 255

ALLOWED_IMAGE_TYPES: dict[str, str] = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}

_SAFE_FOLDER = re.compile(r"^[a-z0-9][a-z0-9_-]{0,49}$")
_PUBLIC_ID_SUFFIX = re.compile(r"^[0-9a-f]{32}$")


@dataclass(frozen=True, slots=True)
class EventImagePolicy:
    """Server-side rules for event images. Nothing here is taken from the client.

    Every image of an event lives under `<folder>/events/<event_id>/<random id>`: the id is chosen
    by the server and signed, so an upload authorized for one event cannot be confirmed for
    another one.
    """

    folder: str = "mis-eventos"
    max_bytes: int = DEFAULT_MAX_IMAGE_BYTES
    allowed_types: dict[str, str] = field(default_factory=lambda: dict(ALLOWED_IMAGE_TYPES))

    def __post_init__(self) -> None:
        if not _SAFE_FOLDER.match(self.folder):
            raise ValueError("Image folder must be lowercase letters, digits, '-' or '_'")
        if self.max_bytes <= 0:
            raise ValueError("Maximum image size must be greater than zero")

    @property
    def allowed_formats(self) -> tuple[str, ...]:
        return tuple(sorted(set(self.allowed_types.values())))

    def ensure_valid_upload(self, filename: str, content_type: str, size: int) -> None:
        if not filename.strip() or len(filename) > MAX_FILENAME_LENGTH:
            raise InvalidValueError("A file name is required")
        if content_type.lower() not in self.allowed_types:
            allowed = ", ".join(self.allowed_types)
            raise InvalidValueError(f"Only these image types are allowed: {allowed}")
        self._ensure_size(size)

    def new_public_id(self, event_id: int) -> str:
        return f"{self.public_id_prefix(event_id)}{uuid4().hex}"

    def belongs_to_event(self, public_id: str, event_id: int) -> bool:
        prefix = self.public_id_prefix(event_id)
        return public_id.startswith(prefix) and bool(
            _PUBLIC_ID_SUFFIX.match(public_id[len(prefix) :])
        )

    def ensure_acceptable(self, image: StoredImage) -> None:
        """Checks the image as stored by the service (the client may have lied about it)."""
        if image.format.lower() not in self.allowed_formats:
            raise InvalidValueError("The uploaded file is not an allowed image format")
        self._ensure_size(image.bytes)

    def public_id_prefix(self, event_id: int) -> str:
        return f"{self.folder}/events/{event_id}/"

    def _ensure_size(self, size: int) -> None:
        if size <= 0:
            raise InvalidValueError("The image is empty")
        if size > self.max_bytes:
            megabytes = self.max_bytes / (1024 * 1024)
            raise InvalidValueError(f"The image must not exceed {megabytes:g} MB")
