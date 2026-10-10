import logging
import time
from collections.abc import Callable
from typing import Any

import cloudinary.api
import cloudinary.exceptions
import cloudinary.uploader
import cloudinary.utils

from app.domain.exceptions import ImageStorageError
from app.domain.ports import ImageStorage, SignedImageUpload, StoredImage

logger = logging.getLogger(__name__)

UPLOAD_URL = "https://api.cloudinary.com/v1_1/{cloud_name}/image/upload"
REQUEST_TIMEOUT_SECONDS = 10


class CloudinaryImageStorage(ImageStorage):
    """Cloudinary through its official SDK.

    Credentials are passed on every call instead of the SDK global configuration, and they are
    never logged nor included in errors: failures are logged with the exception type only.
    """

    def __init__(
        self,
        cloud_name: str,
        api_key: str,
        api_secret: str,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._cloud_name = cloud_name
        self._api_key = api_key
        self._api_secret = api_secret
        self._clock = clock

    def sign_upload(self, public_id: str, allowed_formats: tuple[str, ...]) -> SignedImageUpload:
        timestamp = int(self._clock())
        formats = ",".join(allowed_formats)
        # Cloudinary rejects the upload if any of these values differ from the signed ones, and
        # signatures expire one hour after the timestamp.
        params = {"allowed_formats": formats, "public_id": public_id, "timestamp": timestamp}
        signature = cloudinary.utils.api_sign_request(params, self._api_secret)
        return SignedImageUpload(
            upload_url=UPLOAD_URL.format(cloud_name=self._cloud_name),
            cloud_name=self._cloud_name,
            api_key=self._api_key,
            timestamp=timestamp,
            signature=signature,
            public_id=public_id,
            allowed_formats=formats,
        )

    def get_image(self, public_id: str) -> StoredImage | None:
        try:
            resource = cloudinary.api.resource(
                public_id, resource_type="image", type="upload", **self._options()
            )
        except cloudinary.exceptions.NotFound:
            return None
        except Exception as error:
            raise self._failure("get_image", error) from None
        try:
            return StoredImage(
                public_id=str(resource["public_id"]),
                secure_url=str(resource["secure_url"]),
                width=int(resource["width"]),
                height=int(resource["height"]),
                format=str(resource["format"]),
                bytes=int(resource["bytes"]),
            )
        except (KeyError, TypeError, ValueError) as error:
            raise self._failure("get_image", error) from None

    def delete_image(self, public_id: str) -> None:
        try:
            result = cloudinary.uploader.destroy(
                public_id, resource_type="image", type="upload", invalidate=True, **self._options()
            )
        except Exception as error:
            raise self._failure("delete_image", error) from None
        if result.get("result") not in {"ok", "not found"}:
            raise self._failure("delete_image", None)

    def _options(self) -> dict[str, Any]:
        return {
            "cloud_name": self._cloud_name,
            "api_key": self._api_key,
            "api_secret": self._api_secret,
            "timeout": REQUEST_TIMEOUT_SECONDS,
        }

    @staticmethod
    def _failure(operation: str, error: Exception | None) -> ImageStorageError:
        logger.warning(
            "image_storage_error",
            extra={"operation": operation, "error": type(error).__name__ if error else "result"},
        )
        return ImageStorageError()
