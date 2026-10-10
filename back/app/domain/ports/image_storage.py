from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SignedImageUpload:
    """Parameters the client sends, unchanged, with its direct upload to the image service.

    Only public values: the API secret never leaves the server.
    """

    upload_url: str
    cloud_name: str
    api_key: str
    timestamp: int
    signature: str
    public_id: str
    allowed_formats: str


@dataclass(frozen=True, slots=True)
class StoredImage:
    """Metadata of an image as reported by the image service itself."""

    public_id: str
    secure_url: str
    width: int
    height: int
    format: str
    bytes: int


class ImageStorage(ABC):
    """External image service (upload signing, verification and deletion).

    Failures raise `ImageStorageError`.
    """

    @abstractmethod
    def sign_upload(self, public_id: str, allowed_formats: tuple[str, ...]) -> SignedImageUpload:
        """Sign an upload restricted to this public id and these formats."""

    @abstractmethod
    def get_image(self, public_id: str) -> StoredImage | None:
        """Metadata of an uploaded image, or `None` if it does not exist in the account."""

    @abstractmethod
    def delete_image(self, public_id: str) -> None:
        """Delete the image. Deleting an image that does not exist is not an error."""
