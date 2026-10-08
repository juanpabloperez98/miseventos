import logging

from app.application.dto import LoginCommand
from app.domain.exceptions import InvalidCredentialsError
from app.domain.ports import AccessToken, PasswordHasher, TokenService, UserRepository

logger = logging.getLogger(__name__)


class LoginUserUseCase:
    def __init__(
        self,
        users: UserRepository,
        password_hasher: PasswordHasher,
        token_service: TokenService,
    ) -> None:
        self._users = users
        self._password_hasher = password_hasher
        self._token_service = token_service

    def execute(self, command: LoginCommand) -> AccessToken:
        user = self._users.get_by_email(command.email.strip().lower())
        if (
            user is None
            or user.id is None
            or not self._password_hasher.verify(command.password, user.password_hash)
        ):
            logger.info("login_failed")
            raise InvalidCredentialsError()

        logger.info("login_succeeded", extra={"user_id": user.id})
        return self._token_service.issue(user.id, user.role)
