from dataclasses import asdict
from typing import Any

import cloudinary.api
import cloudinary.exceptions
import cloudinary.uploader
import cloudinary.utils
import pytest

from app.domain.exceptions import ImageStorageError
from app.infrastructure.images import CloudinaryImageStorage

SECRET = "test-api-secret-never-shown"
PUBLIC_ID = "mis-eventos/events/7/0123456789abcdef0123456789abcdef"
RESOURCE = {
    "public_id": PUBLIC_ID,
    "secure_url": f"https://res.cloudinary.com/demo/image/upload/v1/{PUBLIC_ID}.jpg",
    "width": 1600,
    "height": 900,
    "format": "jpg",
    "bytes": 123_456,
    "resource_type": "image",
}


@pytest.fixture
def storage() -> CloudinaryImageStorage:
    return CloudinaryImageStorage("demo", "123456", SECRET, clock=lambda: 1_900_000_000.7)


@pytest.fixture
def calls(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str, dict[str, Any]]]:
    recorded: list[tuple[str, str, dict[str, Any]]] = []

    def fake_resource(public_id: str, **options: Any) -> dict[str, Any]:
        recorded.append(("resource", public_id, options))
        return dict(RESOURCE)

    def fake_destroy(public_id: str, **options: Any) -> dict[str, str]:
        recorded.append(("destroy", public_id, options))
        return {"result": "ok"}

    monkeypatch.setattr(cloudinary.api, "resource", fake_resource)
    monkeypatch.setattr(cloudinary.uploader, "destroy", fake_destroy)
    return recorded


class TestSignUpload:
    def test_signs_exactly_the_server_chosen_parameters(
        self, storage: CloudinaryImageStorage
    ) -> None:
        upload = storage.sign_upload(PUBLIC_ID, ("jpg", "png", "webp"))

        expected = cloudinary.utils.api_sign_request(
            {"allowed_formats": "jpg,png,webp", "public_id": PUBLIC_ID, "timestamp": 1_900_000_000},
            SECRET,
        )
        assert upload.signature == expected
        assert upload.timestamp == 1_900_000_000
        assert upload.public_id == PUBLIC_ID
        assert upload.allowed_formats == "jpg,png,webp"
        assert upload.upload_url == "https://api.cloudinary.com/v1_1/demo/image/upload"
        assert (upload.cloud_name, upload.api_key) == ("demo", "123456")

    def test_never_exposes_the_api_secret(self, storage: CloudinaryImageStorage) -> None:
        upload = storage.sign_upload(PUBLIC_ID, ("jpg",))

        assert SECRET not in str(asdict(upload))

    def test_a_different_public_id_gives_a_different_signature(
        self, storage: CloudinaryImageStorage
    ) -> None:
        first = storage.sign_upload(PUBLIC_ID, ("jpg",)).signature
        second = storage.sign_upload(PUBLIC_ID.replace("events/7", "events/8"), ("jpg",)).signature

        assert first != second


class TestGetImage:
    def test_returns_the_metadata_reported_by_cloudinary(
        self, storage: CloudinaryImageStorage, calls: list[tuple[str, str, dict[str, Any]]]
    ) -> None:
        image = storage.get_image(PUBLIC_ID)

        assert image is not None
        assert (image.width, image.height, image.format, image.bytes) == (1600, 900, "jpg", 123_456)
        assert image.secure_url == RESOURCE["secure_url"]
        [(name, public_id, options)] = calls
        assert (name, public_id) == ("resource", PUBLIC_ID)
        assert options["resource_type"] == "image"
        assert options["type"] == "upload"
        assert options["cloud_name"] == "demo"
        assert options["timeout"] > 0

    def test_returns_none_for_missing_images(
        self, storage: CloudinaryImageStorage, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def not_found(public_id: str, **options: Any) -> dict[str, Any]:
            raise cloudinary.exceptions.NotFound("Resource not found")

        monkeypatch.setattr(cloudinary.api, "resource", not_found)

        assert storage.get_image(PUBLIC_ID) is None

    @pytest.mark.parametrize(
        "error",
        [cloudinary.exceptions.AuthorizationRequired(f"bad key {SECRET}"), TimeoutError("slow")],
    )
    def test_wraps_failures_without_leaking_details(
        self,
        storage: CloudinaryImageStorage,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
        error: Exception,
    ) -> None:
        def failing(public_id: str, **options: Any) -> dict[str, Any]:
            raise error

        monkeypatch.setattr(cloudinary.api, "resource", failing)

        with pytest.raises(ImageStorageError) as raised:
            storage.get_image(PUBLIC_ID)
        assert SECRET not in str(raised.value)
        assert raised.value.__cause__ is None
        assert SECRET not in caplog.text

    def test_rejects_incomplete_responses(
        self, storage: CloudinaryImageStorage, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(cloudinary.api, "resource", lambda public_id, **options: {"width": 1})

        with pytest.raises(ImageStorageError):
            storage.get_image(PUBLIC_ID)


class TestDeleteImage:
    def test_destroys_the_image_and_invalidates_the_cdn(
        self, storage: CloudinaryImageStorage, calls: list[tuple[str, str, dict[str, Any]]]
    ) -> None:
        storage.delete_image(PUBLIC_ID)

        [(name, public_id, options)] = calls
        assert (name, public_id) == ("destroy", PUBLIC_ID)
        assert options["invalidate"] is True
        assert options["resource_type"] == "image"

    def test_missing_images_are_not_an_error(
        self, storage: CloudinaryImageStorage, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            cloudinary.uploader, "destroy", lambda public_id, **options: {"result": "not found"}
        )

        storage.delete_image(PUBLIC_ID)

    @pytest.mark.parametrize("outcome", [{"result": "error"}, ConnectionError("down")])
    def test_failures_raise_an_image_storage_error(
        self,
        storage: CloudinaryImageStorage,
        monkeypatch: pytest.MonkeyPatch,
        outcome: dict[str, str] | Exception,
    ) -> None:
        def destroy(public_id: str, **options: Any) -> dict[str, str]:
            if isinstance(outcome, Exception):
                raise outcome
            return outcome

        monkeypatch.setattr(cloudinary.uploader, "destroy", destroy)

        with pytest.raises(ImageStorageError):
            storage.delete_image(PUBLIC_ID)
