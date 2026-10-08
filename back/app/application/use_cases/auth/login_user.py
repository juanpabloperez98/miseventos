import logging
import secrets

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
        self._unmatchable_password_hash = password_hasher.hash(secrets.token_hex(32))

    def execute(self, command: LoginCommand) -> AccessToken:
        user = self._users.get_by_email(command.email.strip().lower())
        # Unknown emails are verified against an unmatchable hash so both paths take similar time.
        password_hash = user.password_hash if user is not None else self._unmatchable_password_hash
        password_matches = self._password_hasher.verify(command.password, password_hash)

        if user is None or user.id is None or not password_matches:
            logger.info("login_failed")
            raise InvalidCredentialsError()

        logger.info("login_succeeded", extra={"user_id": user.id})
        return self._token_service.issue(user.id, user.role)
