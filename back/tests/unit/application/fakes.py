from dataclasses import replace
from datetime import UTC, datetime

from app.domain.entities import Event, EventImage, Registration, Session, Speaker, User
from app.domain.enums import EventStatus
from app.domain.exceptions import ImageStorageError, NotFoundError
from app.domain.ports import (
    EventImageRepository,
    EventRepository,
    EventSearchCriteria,
    EventVisibility,
    ImageStorage,
    RegistrationRepository,
    SeedRecord,
    SeedRecordRepository,
    SessionRepository,
    SignedImageUpload,
    SpeakerRepository,
    StoredImage,
    UnitOfWork,
    UserRepository,
)
from app.domain.value_objects import Page, PageRequest


class InMemoryUserRepository(UserRepository):
    def __init__(self) -> None:
        self._users: dict[int, User] = {}

    def add(self, user: User) -> User:
        now = datetime.now(UTC)
        stored = replace(user, id=len(self._users) + 1, created_at=now, updated_at=now)
        self._users[stored.id or 0] = stored
        return stored

    def get_by_id(self, user_id: int) -> User | None:
        return self._users.get(user_id)

    def get_by_email(self, email: str) -> User | None:
        return next((user for user in self._users.values() if user.email == email), None)


class InMemoryEventRepository(EventRepository):
    def __init__(self, registrations: "InMemoryRegistrationRepository | None" = None) -> None:
        self._events: dict[int, Event] = {}
        self._next_id = 1
        self._registrations = registrations

    def add(self, event: Event) -> Event:
        now = datetime.now(UTC)
        stored = replace(event, id=self._next_id, created_at=now, updated_at=now)
        self._events[self._next_id] = stored
        self._next_id += 1
        return stored

    def get_by_id(self, event_id: int) -> Event | None:
        return self._events.get(event_id)

    def get_by_id_for_update(self, event_id: int) -> Event | None:
        return self.get_by_id(event_id)

    def update(self, event: Event) -> Event:
        if event.id not in self._events:
            raise NotFoundError.for_entity("Event")
        stored = replace(event, updated_at=datetime.now(UTC))
        self._events[event.id] = stored
        return stored

    def delete(self, event_id: int) -> None:
        if self._events.pop(event_id, None) is None:
            raise NotFoundError.for_entity("Event")

    def search(self, criteria: EventSearchCriteria, page: PageRequest) -> Page[Event]:
        matches = sorted(
            (event for event in self._events.values() if self._matches(event, criteria)),
            key=lambda event: (event.start_date, event.id or 0),
        )
        items = matches[page.offset : page.offset + page.per_page]
        return Page(items=items, total=len(matches), request=page)

    def list_by_attendee(self, user_id: int) -> list[Event]:
        if self._registrations is None:
            return []
        event_ids = self._registrations.event_ids_of(user_id)
        return sorted(
            (event for event in self._events.values() if event.id in event_ids),
            key=lambda event: (event.start_date, event.id or 0),
        )

    @staticmethod
    def _matches(event: Event, criteria: EventSearchCriteria) -> bool:
        if not _is_visible(event, criteria.visibility):
            return False
        if criteria.name and criteria.name.lower() not in event.name.lower():
            return False
        return criteria.status is None or event.status is criteria.status


def _is_visible(event: Event, visibility: EventVisibility) -> bool:
    return (
        visibility.include_unpublished
        or event.status is EventStatus.PUBLISHED
        or event.created_by == visibility.owner_id
    )


class InMemoryRegistrationRepository(RegistrationRepository):
    def __init__(self) -> None:
        self._registrations: dict[int, Registration] = {}

    def add(self, registration: Registration) -> Registration:
        stored = replace(registration, id=len(self._registrations) + 1)
        self._registrations[stored.id or 0] = stored
        return stored

    def get(self, user_id: int, event_id: int) -> Registration | None:
        return next(
            (
                registration
                for registration in self._registrations.values()
                if registration.user_id == user_id and registration.event_id == event_id
            ),
            None,
        )

    def delete(self, registration_id: int) -> None:
        del self._registrations[registration_id]

    def count_by_event(self, event_id: int) -> int:
        return sum(1 for item in self._registrations.values() if item.event_id == event_id)

    def event_ids_of(self, user_id: int) -> set[int]:
        return {item.event_id for item in self._registrations.values() if item.user_id == user_id}


class InMemorySessionRepository(SessionRepository):
    def __init__(self) -> None:
        self._sessions: dict[int, Session] = {}
        self._next_id = 1

    def add(self, session: Session) -> Session:
        stored = replace(session, id=self._next_id)
        self._sessions[self._next_id] = stored
        self._next_id += 1
        return stored

    def get_by_id(self, session_id: int) -> Session | None:
        return self._sessions.get(session_id)

    def update(self, session: Session) -> Session:
        if session.id not in self._sessions:
            raise NotFoundError.for_entity("Session")
        self._sessions[session.id] = session
        return session

    def delete(self, session_id: int) -> None:
        if self._sessions.pop(session_id, None) is None:
            raise NotFoundError.for_entity("Session")

    def list_by_event(self, event_id: int) -> list[Session]:
        return sorted(
            (session for session in self._sessions.values() if session.event_id == event_id),
            key=lambda session: (session.start_time, session.id or 0),
        )


class InMemorySpeakerRepository(SpeakerRepository):
    def __init__(self) -> None:
        self._speakers: dict[int, Speaker] = {}

    def add(self, speaker: Speaker) -> Speaker:
        stored = replace(speaker, id=len(self._speakers) + 1)
        self._speakers[stored.id or 0] = stored
        return stored

    def get_by_id(self, speaker_id: int) -> Speaker | None:
        return self._speakers.get(speaker_id)

    def update(self, speaker: Speaker) -> Speaker:
        raise NotImplementedError

    def delete(self, speaker_id: int) -> None:
        raise NotImplementedError

    def list_all(self, page: PageRequest) -> Page[Speaker]:
        ordered = sorted(self._speakers.values(), key=lambda speaker: (speaker.name, speaker.id))
        start = (page.page - 1) * page.per_page
        return Page(items=ordered[start : start + page.per_page], total=len(ordered), request=page)


class SpyUnitOfWork(UnitOfWork):
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1


class InMemorySeedRecordRepository(SeedRecordRepository):
    def __init__(self) -> None:
        self.records: dict[str, SeedRecord] = {}

    def get(self, seed_key: str) -> SeedRecord | None:
        return self.records.get(seed_key)

    def save(self, record: SeedRecord) -> None:
        self.records[record.seed_key] = record


class InMemoryEventImageRepository(EventImageRepository):
    """Also attaches the image to the event, like the database relationship does."""

    def __init__(self, events: InMemoryEventRepository | None = None) -> None:
        self._images: dict[int, EventImage] = {}
        self._next_id = 1
        self._events = events
        self.fail_on_save = False

    def get_by_event(self, event_id: int) -> EventImage | None:
        return self._images.get(event_id)

    def save(self, image: EventImage) -> EventImage:
        if self.fail_on_save:
            raise RuntimeError("database unavailable")
        current = self._images.get(image.event_id)
        stored = replace(image, id=current.id if current else self._next_id)
        if current is None:
            self._next_id += 1
        self._images[image.event_id] = stored
        self._attach(image.event_id, stored)
        return stored

    def delete_by_event(self, event_id: int) -> None:
        self._images.pop(event_id, None)
        self._attach(event_id, None)

    def _attach(self, event_id: int, image: EventImage | None) -> None:
        event = self._events.get_by_id(event_id) if self._events else None
        if self._events is not None and event is not None:
            self._events.update(replace(event, image=image))


class FakeImageStorage(ImageStorage):
    """Records calls; `images` plays the role of the files stored in the image service."""

    def __init__(self) -> None:
        self.images: dict[str, StoredImage] = {}
        self.signed: list[tuple[str, tuple[str, ...]]] = []
        self.deleted: list[str] = []
        self.fail_get = False
        self.fail_delete = False

    def sign_upload(self, public_id: str, allowed_formats: tuple[str, ...]) -> SignedImageUpload:
        self.signed.append((public_id, allowed_formats))
        return SignedImageUpload(
            upload_url="https://api.cloudinary.com/v1_1/demo/image/upload",
            cloud_name="demo",
            api_key="123",
            timestamp=1_900_000_000,
            signature="signature",
            public_id=public_id,
            allowed_formats=",".join(allowed_formats),
        )

    def get_image(self, public_id: str) -> StoredImage | None:
        if self.fail_get:
            raise ImageStorageError()
        return self.images.get(public_id)

    def delete_image(self, public_id: str) -> None:
        if self.fail_delete:
            raise ImageStorageError()
        self.deleted.append(public_id)
        self.images.pop(public_id, None)

    def upload(self, public_id: str, *, format: str = "jpg", size: int = 2048) -> StoredImage:
        image = StoredImage(
            public_id=public_id,
            secure_url=f"https://res.cloudinary.com/demo/image/upload/v1/{public_id}.{format}",
            width=1600,
            height=900,
            format=format,
            bytes=size,
        )
        self.images[public_id] = image
        return image
