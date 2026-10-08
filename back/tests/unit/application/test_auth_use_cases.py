from datetime import timedelta

import pytest

from app.application.dto import LoginCommand, RegisterUserCommand
from app.application.use_cases.auth import (
    AuthenticateUserUseCase,
    LoginUserUseCase,
    RegisterUserUseCase,
)
from app.domain.enums import UserRole
from app.domain.exceptions import (
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    InvalidTokenError,
    InvalidValueError,
)
from app.infrastructure.security import JwtTokenService, Sha256PasswordHasher
from tests.unit.application.fakes import InMemoryUserRepository, SpyUnitOfWork

SECRET = "unit-test-jwt-secret-key-with-at-least-32-chars"
PASSWORD = "correct-horse-battery"


@pytest.fixture
def users() -> InMemoryUserRepository:
    return InMemoryUserRepository()


@pytest.fixture
def unit_of_work() -> SpyUnitOfWork:
    return SpyUnitOfWork()


@pytest.fixture
def hasher() -> Sha256PasswordHasher:
    return Sha256PasswordHasher()


@pytest.fixture
def tokens() -> JwtTokenService:
    return JwtTokenService(SECRET, timedelta(minutes=10))


@pytest.fixture
def register(
    users: InMemoryUserRepository, hasher: Sha256PasswordHasher, unit_of_work: SpyUnitOfWork
) -> RegisterUserUseCase:
    return RegisterUserUseCase(users, hasher, unit_of_work)


def _register_ada(register: RegisterUserUseCase) -> int:
    return register.execute(RegisterUserCommand("Ada", "Ada@Example.com", PASSWORD)).id


class TestRegisterUser:
    def test_creates_attendee_with_hashed_password_and_commits(
        self,
        register: RegisterUserUseCase,
        users: InMemoryUserRepository,
        hasher: Sha256PasswordHasher,
        unit_of_work: SpyUnitOfWork,
    ) -> None:
        result = register.execute(RegisterUserCommand("Ada", "Ada@Example.com", PASSWORD))

        stored = users.get_by_id(result.id)
        assert stored is not None
        assert result.email == "ada@example.com"
        assert result.role is UserRole.ATTENDEE
        assert stored.password_hash != PASSWORD
        assert hasher.verify(PASSWORD, stored.password_hash)
        assert unit_of_work.commits == 1

    def test_dto_does_not_expose_password_hash(self, register: RegisterUserUseCase) -> None:
        result = register.execute(RegisterUserCommand("Ada", "ada@example.com", PASSWORD))

        assert not hasattr(result, "password_hash")

    def test_rejects_duplicate_email_ignoring_case(
        self, register: RegisterUserUseCase, unit_of_work: SpyUnitOfWork
    ) -> None:
        _register_ada(register)

        with pytest.raises(EmailAlreadyRegisteredError):
            register.execute(RegisterUserCommand("Other", " ADA@example.com", PASSWORD))
        assert unit_of_work.commits == 1

    def test_rejects_invalid_email(self, register: RegisterUserUseCase) -> None:
        with pytest.raises(InvalidValueError):
            register.execute(RegisterUserCommand("Ada", "not-an-email", PASSWORD))


class TestLoginUser:
    def test_returns_token_for_valid_credentials(
        self,
        register: RegisterUserUseCase,
        users: InMemoryUserRepository,
        hasher: Sha256PasswordHasher,
        tokens: JwtTokenService,
    ) -> None:
        user_id = _register_ada(register)

        token = LoginUserUseCase(users, hasher, tokens).execute(
            LoginCommand(" ADA@example.com ", PASSWORD)
        )

        assert tokens.decode(token.value).user_id == user_id

    @pytest.mark.parametrize(
        ("email", "password"), [("ada@example.com", "wrong-password"), ("nobody@x.io", PASSWORD)]
    )
    def test_rejects_invalid_credentials(
        self,
        register: RegisterUserUseCase,
        users: InMemoryUserRepository,
        hasher: Sha256PasswordHasher,
        tokens: JwtTokenService,
        email: str,
        password: str,
    ) -> None:
        _register_ada(register)

        with pytest.raises(InvalidCredentialsError):
            LoginUserUseCase(users, hasher, tokens).execute(LoginCommand(email, password))


class TestAuthenticateUser:
    def test_resolves_user_from_token(
        self, register: RegisterUserUseCase, users: InMemoryUserRepository, tokens: JwtTokenService
    ) -> None:
        user_id = _register_ada(register)
        token = tokens.issue(user_id, UserRole.ATTENDEE)

        user = AuthenticateUserUseCase(users, tokens).execute(token.value)

        assert user.id == user_id
        assert user.email == "ada@example.com"

    def test_rejects_token_of_unknown_user(
        self, users: InMemoryUserRepository, tokens: JwtTokenService
    ) -> None:
        token = tokens.issue(999, UserRole.ADMIN)

        with pytest.raises(InvalidTokenError):
            AuthenticateUserUseCase(users, tokens).execute(token.value)
