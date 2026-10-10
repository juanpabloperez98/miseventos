from dataclasses import replace

import pytest

from app.application.dto import Actor, ConfirmImageCommand, ImageUploadRequest
from app.application.services import AuthorizationService, EventAccessPolicy, EventImagePolicy
from app.application.use_cases.event_images import (
    AuthorizeEventImageUploadUseCase,
    ConfirmEventImageUseCase,
    DeleteEventImageUseCase,
)
from app.application.use_cases.events import DeleteEventUseCase
from app.domain.entities import Event
from app.domain.enums import EventRemoval, EventStatus, UserRole
from app.domain.exceptions import (
    AuthorizationError,
    EventNotEditableError,
    ImageStorageError,
    InvalidValueError,
    NotFoundError,
)
from tests.factories import build_event
from tests.unit.application.fakes import (
    FakeImageStorage,
    InMemoryEventImageRepository,
    InMemoryEventRepository,
    SpyUnitOfWork,
)

OWNER = Actor(user_id=10, role=UserRole.ORGANIZER)
OTHER_ORGANIZER = Actor(user_id=20, role=UserRole.ORGANIZER)
ADMIN = Actor(user_id=1, role=UserRole.ADMIN)
ATTENDEE = Actor(user_id=30, role=UserRole.ATTENDEE)
MAX_BYTES = 1024 * 1024


@pytest.fixture
def events() -> InMemoryEventRepository:
    return InMemoryEventRepository()


@pytest.fixture
def images(events: InMemoryEventRepository) -> InMemoryEventImageRepository:
    return InMemoryEventImageRepository(events)


@pytest.fixture
def storage() -> FakeImageStorage:
    return FakeImageStorage()


@pytest.fixture
def unit_of_work() -> SpyUnitOfWork:
    return SpyUnitOfWork()


@pytest.fixture
def access_policy() -> EventAccessPolicy:
    return EventAccessPolicy(AuthorizationService())


@pytest.fixture
def image_policy() -> EventImagePolicy:
    return EventImagePolicy(folder="tests", max_bytes=MAX_BYTES)


@pytest.fixture
def event(events: InMemoryEventRepository) -> Event:
    return events.add(build_event(created_by=OWNER.user_id, status=EventStatus.DRAFT))


@pytest.fixture
def authorize(
    events: InMemoryEventRepository,
    access_policy: EventAccessPolicy,
    storage: FakeImageStorage,
    image_policy: EventImagePolicy,
) -> AuthorizeEventImageUploadUseCase:
    return AuthorizeEventImageUploadUseCase(events, access_policy, storage, image_policy)


@pytest.fixture
def confirm(
    events: InMemoryEventRepository,
    images: InMemoryEventImageRepository,
    access_policy: EventAccessPolicy,
    storage: FakeImageStorage,
    image_policy: EventImagePolicy,
    unit_of_work: SpyUnitOfWork,
) -> ConfirmEventImageUseCase:
    return ConfirmEventImageUseCase(
        events, images, access_policy, storage, image_policy, unit_of_work
    )


@pytest.fixture
def delete_image(
    events: InMemoryEventRepository,
    images: InMemoryEventImageRepository,
    access_policy: EventAccessPolicy,
    storage: FakeImageStorage,
    unit_of_work: SpyUnitOfWork,
) -> DeleteEventImageUseCase:
    return DeleteEventImageUseCase(events, images, access_policy, storage, unit_of_work)


def _request(event: Event, **overrides: object) -> ImageUploadRequest:
    values: dict[str, object] = {
        "event_id": event.id or 0,
        "filename": "cover.jpg",
        "content_type": "image/jpeg",
        "size": 200_000,
    }
    values.update(overrides)
    return ImageUploadRequest(**values)  # type: ignore[arg-type]


def _uploaded(
    authorize: AuthorizeEventImageUploadUseCase,
    storage: FakeImageStorage,
    event: Event,
    **upload: object,
) -> str:
    public_id = authorize.execute(OWNER, _request(event)).public_id
    storage.upload(public_id, **upload)  # type: ignore[arg-type]
    return public_id


class TestAuthorizeUpload:
    @pytest.mark.parametrize("actor", [OWNER, ADMIN])
    def test_signs_an_upload_restricted_to_a_server_chosen_id_and_formats(
        self,
        authorize: AuthorizeEventImageUploadUseCase,
        storage: FakeImageStorage,
        event: Event,
        actor: Actor,
    ) -> None:
        upload = authorize.execute(actor, _request(event))

        assert upload.public_id.startswith(f"tests/events/{event.id}/")
        assert storage.signed == [(upload.public_id, ("jpg", "png", "webp"))]
        assert upload.allowed_formats == "jpg,png,webp"

    def test_each_upload_gets_a_new_public_id(
        self, authorize: AuthorizeEventImageUploadUseCase, event: Event
    ) -> None:
        first = authorize.execute(OWNER, _request(event)).public_id
        second = authorize.execute(OWNER, _request(event)).public_id

        assert first != second

    def test_ignores_the_file_name_when_choosing_the_public_id(
        self, authorize: AuthorizeEventImageUploadUseCase, event: Event
    ) -> None:
        upload = authorize.execute(OWNER, _request(event, filename="../../other/evil.jpg"))

        assert "evil" not in upload.public_id
        assert ".." not in upload.public_id

    @pytest.mark.parametrize("actor", [OTHER_ORGANIZER, ATTENDEE])
    def test_rejects_users_who_cannot_manage_the_event(
        self,
        authorize: AuthorizeEventImageUploadUseCase,
        storage: FakeImageStorage,
        event: Event,
        actor: Actor,
    ) -> None:
        with pytest.raises(AuthorizationError):
            authorize.execute(actor, _request(event))
        assert storage.signed == []

    def test_rejects_unknown_events(self, authorize: AuthorizeEventImageUploadUseCase) -> None:
        with pytest.raises(NotFoundError):
            authorize.execute(
                OWNER,
                ImageUploadRequest(
                    event_id=999, filename="a.jpg", content_type="image/png", size=1
                ),
            )

    def test_rejects_final_events(
        self,
        authorize: AuthorizeEventImageUploadUseCase,
        events: InMemoryEventRepository,
        event: Event,
    ) -> None:
        events.update(replace(event, status=EventStatus.CANCELLED))

        with pytest.raises(EventNotEditableError):
            authorize.execute(OWNER, _request(event))

    @pytest.mark.parametrize(
        "content_type", ["image/gif", "image/svg+xml", "application/pdf", "text/html"]
    )
    def test_rejects_types_that_are_not_allowed(
        self,
        authorize: AuthorizeEventImageUploadUseCase,
        storage: FakeImageStorage,
        event: Event,
        content_type: str,
    ) -> None:
        with pytest.raises(InvalidValueError, match="image types"):
            authorize.execute(OWNER, _request(event, content_type=content_type))
        assert storage.signed == []

    @pytest.mark.parametrize("content_type", ["image/jpeg", "IMAGE/PNG", "image/webp"])
    def test_accepts_the_allowed_types(
        self, authorize: AuthorizeEventImageUploadUseCase, event: Event, content_type: str
    ) -> None:
        assert authorize.execute(OWNER, _request(event, content_type=content_type)).signature

    def test_rejects_files_that_are_too_large(
        self, authorize: AuthorizeEventImageUploadUseCase, event: Event
    ) -> None:
        with pytest.raises(InvalidValueError, match="1 MB"):
            authorize.execute(OWNER, _request(event, size=MAX_BYTES + 1))

    def test_accepts_files_of_the_maximum_size(
        self, authorize: AuthorizeEventImageUploadUseCase, event: Event
    ) -> None:
        assert authorize.execute(OWNER, _request(event, size=MAX_BYTES)).signature

    @pytest.mark.parametrize("filename", ["", "   ", "a" * 256])
    def test_rejects_invalid_file_names(
        self, authorize: AuthorizeEventImageUploadUseCase, event: Event, filename: str
    ) -> None:
        with pytest.raises(InvalidValueError):
            authorize.execute(OWNER, _request(event, filename=filename))


class TestConfirmImage:
    def test_stores_the_metadata_reported_by_the_image_service(
        self,
        authorize: AuthorizeEventImageUploadUseCase,
        confirm: ConfirmEventImageUseCase,
        storage: FakeImageStorage,
        events: InMemoryEventRepository,
        unit_of_work: SpyUnitOfWork,
        event: Event,
    ) -> None:
        public_id = _uploaded(authorize, storage, event, format="png", size=4096)

        image = confirm.execute(OWNER, ConfirmImageCommand(event.id or 0, public_id))

        stored = storage.images[public_id]
        assert (image.public_id, image.secure_url, image.width, image.height) == (
            stored.public_id,
            stored.secure_url,
            stored.width,
            stored.height,
        )
        assert (image.format, image.bytes) == ("png", 4096)
        assert unit_of_work.commits == 1
        assert events.get_by_id(event.id or 0).image == image  # type: ignore[union-attr]
        assert storage.deleted == []

    def test_is_idempotent_for_the_current_image(
        self,
        authorize: AuthorizeEventImageUploadUseCase,
        confirm: ConfirmEventImageUseCase,
        storage: FakeImageStorage,
        unit_of_work: SpyUnitOfWork,
        event: Event,
    ) -> None:
        public_id = _uploaded(authorize, storage, event)
        command = ConfirmImageCommand(event.id or 0, public_id)

        first = confirm.execute(OWNER, command)
        second = confirm.execute(OWNER, command)

        assert first == second
        assert unit_of_work.commits == 1
        assert storage.deleted == []

    def test_replaces_the_cover_and_deletes_the_previous_one_after_saving(
        self,
        authorize: AuthorizeEventImageUploadUseCase,
        confirm: ConfirmEventImageUseCase,
        storage: FakeImageStorage,
        images: InMemoryEventImageRepository,
        event: Event,
    ) -> None:
        old = _uploaded(authorize, storage, event)
        confirm.execute(OWNER, ConfirmImageCommand(event.id or 0, old))
        new = _uploaded(authorize, storage, event)

        image = confirm.execute(OWNER, ConfirmImageCommand(event.id or 0, new))

        assert image.public_id == new
        assert images.get_by_event(event.id or 0) == image
        assert storage.deleted == [old]

    def test_keeps_the_previous_cover_and_discards_the_new_upload_if_saving_fails(
        self,
        authorize: AuthorizeEventImageUploadUseCase,
        confirm: ConfirmEventImageUseCase,
        storage: FakeImageStorage,
        images: InMemoryEventImageRepository,
        unit_of_work: SpyUnitOfWork,
        event: Event,
    ) -> None:
        old = _uploaded(authorize, storage, event)
        confirm.execute(OWNER, ConfirmImageCommand(event.id or 0, old))
        new = _uploaded(authorize, storage, event)
        images.fail_on_save = True

        with pytest.raises(RuntimeError):
            confirm.execute(OWNER, ConfirmImageCommand(event.id or 0, new))

        assert images.get_by_event(event.id or 0).public_id == old  # type: ignore[union-attr]
        assert storage.deleted == [new]
        assert old in storage.images
        assert unit_of_work.rollbacks >= 1

    def test_a_failed_cleanup_of_the_previous_cover_does_not_undo_the_replacement(
        self,
        authorize: AuthorizeEventImageUploadUseCase,
        confirm: ConfirmEventImageUseCase,
        storage: FakeImageStorage,
        images: InMemoryEventImageRepository,
        event: Event,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        old = _uploaded(authorize, storage, event)
        confirm.execute(OWNER, ConfirmImageCommand(event.id or 0, old))
        new = _uploaded(authorize, storage, event)
        storage.fail_delete = True

        image = confirm.execute(OWNER, ConfirmImageCommand(event.id or 0, new))

        assert images.get_by_event(event.id or 0) == image
        assert "event_image_cleanup_failed" in caplog.text

    def test_rejects_images_that_the_service_does_not_have(
        self,
        authorize: AuthorizeEventImageUploadUseCase,
        confirm: ConfirmEventImageUseCase,
        images: InMemoryEventImageRepository,
        event: Event,
    ) -> None:
        public_id = authorize.execute(OWNER, _request(event)).public_id

        with pytest.raises(InvalidValueError, match="could not be verified"):
            confirm.execute(OWNER, ConfirmImageCommand(event.id or 0, public_id))
        assert images.get_by_event(event.id or 0) is None

    def test_does_not_save_anything_if_the_service_fails(
        self,
        authorize: AuthorizeEventImageUploadUseCase,
        confirm: ConfirmEventImageUseCase,
        storage: FakeImageStorage,
        images: InMemoryEventImageRepository,
        event: Event,
    ) -> None:
        public_id = _uploaded(authorize, storage, event)
        storage.fail_get = True

        with pytest.raises(ImageStorageError):
            confirm.execute(OWNER, ConfirmImageCommand(event.id or 0, public_id))
        assert images.get_by_event(event.id or 0) is None

    def test_rejects_images_uploaded_for_another_event(
        self,
        authorize: AuthorizeEventImageUploadUseCase,
        confirm: ConfirmEventImageUseCase,
        storage: FakeImageStorage,
        events: InMemoryEventRepository,
        event: Event,
    ) -> None:
        other = events.add(build_event(created_by=OWNER.user_id, status=EventStatus.DRAFT))
        public_id = _uploaded(authorize, storage, other)

        with pytest.raises(InvalidValueError, match="not uploaded for this event"):
            confirm.execute(OWNER, ConfirmImageCommand(event.id or 0, public_id))
        assert public_id in storage.images

    @pytest.mark.parametrize(
        "public_id",
        [
            "tests/events/1/../2/0123456789abcdef0123456789abcdef",
            "other/events/1/0123456789abcdef0123456789abcdef",
            "tests/events/1/chosen-by-the-client",
            "tests/events/10/0123456789abcdef0123456789abcdef",
        ],
    )
    def test_rejects_public_ids_not_issued_for_the_event(
        self, confirm: ConfirmEventImageUseCase, event: Event, public_id: str
    ) -> None:
        assert event.id == 1
        with pytest.raises(InvalidValueError):
            confirm.execute(OWNER, ConfirmImageCommand(1, public_id))

    @pytest.mark.parametrize(
        ("upload", "message"), [({"format": "gif"}, "format"), ({"size": MAX_BYTES + 1}, "1 MB")]
    )
    def test_rejects_and_deletes_uploads_that_break_the_rules(
        self,
        authorize: AuthorizeEventImageUploadUseCase,
        confirm: ConfirmEventImageUseCase,
        storage: FakeImageStorage,
        images: InMemoryEventImageRepository,
        event: Event,
        upload: dict[str, object],
        message: str,
    ) -> None:
        public_id = _uploaded(authorize, storage, event, **upload)

        with pytest.raises(InvalidValueError, match=message):
            confirm.execute(OWNER, ConfirmImageCommand(event.id or 0, public_id))
        assert storage.deleted == [public_id]
        assert images.get_by_event(event.id or 0) is None

    @pytest.mark.parametrize("actor", [OTHER_ORGANIZER, ATTENDEE])
    def test_rejects_users_who_cannot_manage_the_event(
        self,
        authorize: AuthorizeEventImageUploadUseCase,
        confirm: ConfirmEventImageUseCase,
        storage: FakeImageStorage,
        images: InMemoryEventImageRepository,
        event: Event,
        actor: Actor,
    ) -> None:
        public_id = _uploaded(authorize, storage, event)

        with pytest.raises(AuthorizationError):
            confirm.execute(actor, ConfirmImageCommand(event.id or 0, public_id))
        assert images.get_by_event(event.id or 0) is None
        assert storage.deleted == []


class TestDeleteImage:
    def test_removes_the_cover_then_deletes_the_file(
        self,
        authorize: AuthorizeEventImageUploadUseCase,
        confirm: ConfirmEventImageUseCase,
        delete_image: DeleteEventImageUseCase,
        storage: FakeImageStorage,
        images: InMemoryEventImageRepository,
        unit_of_work: SpyUnitOfWork,
        event: Event,
    ) -> None:
        public_id = _uploaded(authorize, storage, event)
        confirm.execute(OWNER, ConfirmImageCommand(event.id or 0, public_id))

        delete_image.execute(OWNER, event.id or 0)

        assert images.get_by_event(event.id or 0) is None
        assert storage.deleted == [public_id]
        assert unit_of_work.commits == 2

    def test_the_cover_is_removed_even_if_the_file_cannot_be_deleted(
        self,
        authorize: AuthorizeEventImageUploadUseCase,
        confirm: ConfirmEventImageUseCase,
        delete_image: DeleteEventImageUseCase,
        storage: FakeImageStorage,
        images: InMemoryEventImageRepository,
        event: Event,
    ) -> None:
        confirm.execute(
            OWNER, ConfirmImageCommand(event.id or 0, _uploaded(authorize, storage, event))
        )
        storage.fail_delete = True

        delete_image.execute(OWNER, event.id or 0)

        assert images.get_by_event(event.id or 0) is None

    def test_events_without_cover_answer_not_found(
        self, delete_image: DeleteEventImageUseCase, event: Event
    ) -> None:
        with pytest.raises(NotFoundError):
            delete_image.execute(OWNER, event.id or 0)

    def test_rejects_users_who_cannot_manage_the_event(
        self,
        authorize: AuthorizeEventImageUploadUseCase,
        confirm: ConfirmEventImageUseCase,
        delete_image: DeleteEventImageUseCase,
        storage: FakeImageStorage,
        event: Event,
    ) -> None:
        public_id = _uploaded(authorize, storage, event)
        confirm.execute(OWNER, ConfirmImageCommand(event.id or 0, public_id))

        with pytest.raises(AuthorizationError):
            delete_image.execute(OTHER_ORGANIZER, event.id or 0)
        assert storage.deleted == []


class TestDeleteEventWithImage:
    @pytest.fixture
    def delete_event(
        self,
        events: InMemoryEventRepository,
        access_policy: EventAccessPolicy,
        unit_of_work: SpyUnitOfWork,
        storage: FakeImageStorage,
    ) -> DeleteEventUseCase:
        return DeleteEventUseCase(events, access_policy, unit_of_work, storage)

    def test_deleting_a_draft_deletes_its_image_after_the_commit(
        self,
        authorize: AuthorizeEventImageUploadUseCase,
        confirm: ConfirmEventImageUseCase,
        delete_event: DeleteEventUseCase,
        storage: FakeImageStorage,
        event: Event,
    ) -> None:
        public_id = _uploaded(authorize, storage, event)
        confirm.execute(OWNER, ConfirmImageCommand(event.id or 0, public_id))

        result = delete_event.execute(OWNER, event.id or 0)

        assert result.action is EventRemoval.DELETE
        assert storage.deleted == [public_id]

    def test_cancelling_a_published_event_keeps_its_image(
        self,
        authorize: AuthorizeEventImageUploadUseCase,
        confirm: ConfirmEventImageUseCase,
        delete_event: DeleteEventUseCase,
        storage: FakeImageStorage,
        events: InMemoryEventRepository,
        event: Event,
    ) -> None:
        public_id = _uploaded(authorize, storage, event)
        confirm.execute(OWNER, ConfirmImageCommand(event.id or 0, public_id))
        current = events.get_by_id(event.id or 0)
        assert current is not None
        events.update(replace(current, status=EventStatus.PUBLISHED))

        result = delete_event.execute(OWNER, event.id or 0)

        assert result.action is EventRemoval.CANCEL
        assert storage.deleted == []

    def test_a_failed_image_cleanup_does_not_undo_the_deletion(
        self,
        authorize: AuthorizeEventImageUploadUseCase,
        confirm: ConfirmEventImageUseCase,
        delete_event: DeleteEventUseCase,
        storage: FakeImageStorage,
        events: InMemoryEventRepository,
        event: Event,
    ) -> None:
        confirm.execute(
            OWNER, ConfirmImageCommand(event.id or 0, _uploaded(authorize, storage, event))
        )
        storage.fail_delete = True

        delete_event.execute(OWNER, event.id or 0)

        assert events.get_by_id(event.id or 0) is None


class TestEventImagePolicy:
    @pytest.mark.parametrize("folder", ["", "Upper", "a/b", "../x", "x" * 51])
    def test_rejects_unsafe_folders(self, folder: str) -> None:
        with pytest.raises(ValueError, match="folder"):
            EventImagePolicy(folder=folder)

    def test_rejects_a_non_positive_size_limit(self) -> None:
        with pytest.raises(ValueError, match="size"):
            EventImagePolicy(max_bytes=0)
