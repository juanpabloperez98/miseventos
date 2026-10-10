from collections.abc import Callable
from datetime import timedelta

from sqlalchemy.orm import Session

from app.application.services import AuthorizationService, EventAccessPolicy, EventImagePolicy
from app.application.use_cases.auth import (
    AuthenticateUserUseCase,
    LoginUserUseCase,
    RegisterUserUseCase,
)
from app.application.use_cases.event_images import (
    AuthorizeEventImageUploadUseCase,
    ConfirmEventImageUseCase,
    DeleteEventImageUseCase,
)
from app.application.use_cases.events import (
    CreateEventUseCase,
    DeleteEventUseCase,
    GetEventUseCase,
    ListEventsUseCase,
    UpdateEventUseCase,
)
from app.application.use_cases.registrations import (
    ListMyRegisteredEventsUseCase,
    RegisterForEventUseCase,
)
from app.application.use_cases.seeding import SeedInitialDataUseCase
from app.application.use_cases.sessions import (
    CreateSessionUseCase,
    DeleteSessionUseCase,
    GetSessionUseCase,
    ListEventSessionsUseCase,
    UpdateSessionUseCase,
)
from app.application.use_cases.speakers import ListSpeakersUseCase
from app.domain.ports import ImageStorage, PasswordHasher, TokenService
from app.infrastructure.config import ConfigurationError, Settings
from app.infrastructure.database.repositories import (
    SqlAlchemyEventImageRepository,
    SqlAlchemyEventRepository,
    SqlAlchemyRegistrationRepository,
    SqlAlchemySeedRecordRepository,
    SqlAlchemySessionRepository,
    SqlAlchemySpeakerRepository,
    SqlAlchemyUserRepository,
)
from app.infrastructure.database.session import create_database_engine, create_session_factory
from app.infrastructure.database.unit_of_work import SqlAlchemyUnitOfWork
from app.infrastructure.images import CloudinaryImageStorage, DisabledImageStorage
from app.infrastructure.security import JwtTokenService, Sha256PasswordHasher


class Container:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.engine = create_database_engine(settings.database_url)
        self.session_factory: Callable[[], Session] = create_session_factory(self.engine)
        self.password_hasher: PasswordHasher = Sha256PasswordHasher()
        self.token_service: TokenService = JwtTokenService(
            settings.jwt_secret_key, timedelta(minutes=settings.jwt_expiration_minutes)
        )
        self.authorization_service = AuthorizationService()
        self.event_access_policy = EventAccessPolicy(self.authorization_service)
        self.image_storage: ImageStorage = _create_image_storage(settings)
        try:
            self.event_image_policy = EventImagePolicy(
                folder=settings.cloudinary_folder, max_bytes=settings.event_image_max_bytes
            )
        except ValueError as error:
            raise ConfigurationError(f"CLOUDINARY_FOLDER: {error}") from error

    def create_request_scope(self) -> "RequestScope":
        return RequestScope(self, self.session_factory())


class RequestScope:
    """Builds use cases that share one database session for the lifetime of a request."""

    def __init__(self, container: Container, session: Session) -> None:
        self._container = container
        self._session = session

    @property
    def authorization(self) -> AuthorizationService:
        return self._container.authorization_service

    def register_user(self) -> RegisterUserUseCase:
        return RegisterUserUseCase(
            SqlAlchemyUserRepository(self._session),
            self._container.password_hasher,
            SqlAlchemyUnitOfWork(self._session),
        )

    def login_user(self) -> LoginUserUseCase:
        return LoginUserUseCase(
            SqlAlchemyUserRepository(self._session),
            self._container.password_hasher,
            self._container.token_service,
        )

    def authenticate_user(self) -> AuthenticateUserUseCase:
        return AuthenticateUserUseCase(
            SqlAlchemyUserRepository(self._session), self._container.token_service
        )

    def list_events(self) -> ListEventsUseCase:
        return ListEventsUseCase(
            SqlAlchemyEventRepository(self._session), self._container.event_access_policy
        )

    def get_event(self) -> GetEventUseCase:
        return GetEventUseCase(
            SqlAlchemyEventRepository(self._session), self._container.event_access_policy
        )

    def create_event(self) -> CreateEventUseCase:
        return CreateEventUseCase(
            SqlAlchemyEventRepository(self._session),
            self._container.event_access_policy,
            SqlAlchemyUnitOfWork(self._session),
        )

    def update_event(self) -> UpdateEventUseCase:
        return UpdateEventUseCase(
            SqlAlchemyEventRepository(self._session),
            SqlAlchemyRegistrationRepository(self._session),
            self._container.event_access_policy,
            SqlAlchemyUnitOfWork(self._session),
        )

    def delete_event(self) -> DeleteEventUseCase:
        return DeleteEventUseCase(
            SqlAlchemyEventRepository(self._session),
            self._container.event_access_policy,
            SqlAlchemyUnitOfWork(self._session),
            self._container.image_storage,
        )

    def authorize_event_image_upload(self) -> AuthorizeEventImageUploadUseCase:
        return AuthorizeEventImageUploadUseCase(
            SqlAlchemyEventRepository(self._session),
            self._container.event_access_policy,
            self._container.image_storage,
            self._container.event_image_policy,
        )

    def confirm_event_image(self) -> ConfirmEventImageUseCase:
        return ConfirmEventImageUseCase(
            SqlAlchemyEventRepository(self._session),
            SqlAlchemyEventImageRepository(self._session),
            self._container.event_access_policy,
            self._container.image_storage,
            self._container.event_image_policy,
            SqlAlchemyUnitOfWork(self._session),
        )

    def delete_event_image(self) -> DeleteEventImageUseCase:
        return DeleteEventImageUseCase(
            SqlAlchemyEventRepository(self._session),
            SqlAlchemyEventImageRepository(self._session),
            self._container.event_access_policy,
            self._container.image_storage,
            SqlAlchemyUnitOfWork(self._session),
        )

    def list_event_sessions(self) -> ListEventSessionsUseCase:
        return ListEventSessionsUseCase(
            SqlAlchemySessionRepository(self._session),
            SqlAlchemySpeakerRepository(self._session),
            self.get_event(),
        )

    def get_session(self) -> GetSessionUseCase:
        return GetSessionUseCase(
            SqlAlchemySessionRepository(self._session),
            SqlAlchemyEventRepository(self._session),
            SqlAlchemySpeakerRepository(self._session),
            self._container.event_access_policy,
        )

    def create_session(self) -> CreateSessionUseCase:
        return CreateSessionUseCase(
            SqlAlchemySessionRepository(self._session),
            SqlAlchemyEventRepository(self._session),
            SqlAlchemySpeakerRepository(self._session),
            self._container.event_access_policy,
            SqlAlchemyUnitOfWork(self._session),
        )

    def update_session(self) -> UpdateSessionUseCase:
        return UpdateSessionUseCase(
            SqlAlchemySessionRepository(self._session),
            SqlAlchemyEventRepository(self._session),
            SqlAlchemySpeakerRepository(self._session),
            self._container.event_access_policy,
            SqlAlchemyUnitOfWork(self._session),
        )

    def delete_session(self) -> DeleteSessionUseCase:
        return DeleteSessionUseCase(
            SqlAlchemySessionRepository(self._session),
            SqlAlchemyEventRepository(self._session),
            self._container.event_access_policy,
            SqlAlchemyUnitOfWork(self._session),
        )

    def register_for_event(self) -> RegisterForEventUseCase:
        return RegisterForEventUseCase(
            SqlAlchemyEventRepository(self._session),
            SqlAlchemyRegistrationRepository(self._session),
            self._container.authorization_service,
            self._container.event_access_policy,
            SqlAlchemyUnitOfWork(self._session),
        )

    def list_my_registered_events(self) -> ListMyRegisteredEventsUseCase:
        return ListMyRegisteredEventsUseCase(SqlAlchemyEventRepository(self._session))

    def list_speakers(self) -> ListSpeakersUseCase:
        return ListSpeakersUseCase(SqlAlchemySpeakerRepository(self._session))

    def seed_initial_data(self) -> SeedInitialDataUseCase:
        return SeedInitialDataUseCase(
            SqlAlchemyUserRepository(self._session),
            SqlAlchemySpeakerRepository(self._session),
            SqlAlchemyEventRepository(self._session),
            SqlAlchemySessionRepository(self._session),
            SqlAlchemySeedRecordRepository(self._session),
            self._container.password_hasher,
            SqlAlchemyUnitOfWork(self._session),
        )

    def close(self) -> None:
        self._session.close()


def _create_image_storage(settings: Settings) -> ImageStorage:
    if not settings.cloudinary_enabled:
        return DisabledImageStorage()
    return CloudinaryImageStorage(
        settings.cloudinary_cloud_name, settings.cloudinary_api_key, settings.cloudinary_api_secret
    )
