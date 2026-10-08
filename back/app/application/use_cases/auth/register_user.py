import logging

from app.application.dto import RegisterUserCommand, UserDTO
from app.domain.entities import User
from app.domain.enums import UserRole
from app.domain.exceptions import EmailAlreadyRegisteredError
from app.domain.ports import PasswordHasher, UnitOfWork, UserRepository
from app.domain.value_objects import Email

logger = logging.getLogger(__name__)


class RegisterUserUseCase:
    def __init__(
        self,
        users: UserRepository,
        password_hasher: PasswordHasher,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._users = users
        self._password_hasher = password_hasher
        self._unit_of_work = unit_of_work

    def execute(self, command: RegisterUserCommand) -> UserDTO:
        email = Email(command.email).value
        if self._users.get_by_email(email) is not None:
            raise EmailAlreadyRegisteredError()

        user = self._users.add(
            User(
                name=command.name,
                email=email,
                password_hash=self._password_hasher.hash(command.password),
                role=UserRole.ATTENDEE,
            )
        )
        self._unit_of_work.commit()

        logger.info("user_registered", extra={"user_id": user.id})
        return UserDTO.from_entity(user)
