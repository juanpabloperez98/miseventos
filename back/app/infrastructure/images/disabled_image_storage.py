from app.domain.exceptions import ImageStorageUnavailableError
from app.domain.ports import ImageStorage, SignedImageUpload, StoredImage


class DisabledImageStorage(ImageStorage):
    """Used when Cloudinary is not configured: image operations answer 503, the rest works."""

    def sign_upload(self, public_id: str, allowed_formats: tuple[str, ...]) -> SignedImageUpload:
        raise ImageStorageUnavailableError()

    def get_image(self, public_id: str) -> StoredImage | None:
        raise ImageStorageUnavailableError()

    def delete_image(self, public_id: str) -> None:
        raise ImageStorageUnavailableError()
