from collections.abc import Callable
from datetime import timedelta

from sqlalchemy.orm import Session

from app.application.services import AuthorizationService, EventAccessPolicy
from app.application.use_cases.auth import (
    AuthenticateUserUseCase,
    LoginUserUseCase,
    RegisterUserUseCase,
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
from app.application.use_cases.sessions import (
    CreateSessionUseCase,
    DeleteSessionUseCase,
    GetSessionUseCase,
    ListEventSessionsUseCase,
    UpdateSessionUseCase,
)
from app.domain.ports import PasswordHasher, TokenService
from app.infrastructure.config import Settings
from app.infrastructure.database.repositories import (
    SqlAlchemyEventRepository,
    SqlAlchemyRegistrationRepository,
    SqlAlchemySessionRepository,
    SqlAlchemySpeakerRepository,
    SqlAlchemyUserRepository,
)
from app.infrastructure.database.session import create_database_engine, create_session_factory
from app.infrastructure.database.unit_of_work import SqlAlchemyUnitOfWork
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
        )

    def list_event_sessions(self) -> ListEventSessionsUseCase:
        return ListEventSessionsUseCase(
            SqlAlchemySessionRepository(self._session), self.get_event()
        )

    def get_session(self) -> GetSessionUseCase:
        return GetSessionUseCase(
            SqlAlchemySessionRepository(self._session),
            SqlAlchemyEventRepository(self._session),
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

    def close(self) -> None:
        self._session.close()
