from collections.abc import Callable
from datetime import timedelta

from sqlalchemy.orm import Session

from app.application.services import AuthorizationService
from app.application.use_cases.auth import (
    AuthenticateUserUseCase,
    LoginUserUseCase,
    RegisterUserUseCase,
)
from app.application.use_cases.events import ListPublishedEventsUseCase
from app.domain.ports import PasswordHasher, TokenService
from app.infrastructure.config import Settings
from app.infrastructure.database.repositories import (
    SqlAlchemyEventRepository,
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

    def list_published_events(self) -> ListPublishedEventsUseCase:
        return ListPublishedEventsUseCase(SqlAlchemyEventRepository(self._session))

    def close(self) -> None:
        self._session.close()
