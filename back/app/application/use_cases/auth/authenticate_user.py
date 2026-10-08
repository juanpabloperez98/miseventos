from app.application.dto import UserDTO
from app.domain.exceptions import InvalidTokenError
from app.domain.ports import TokenService, UserRepository


class AuthenticateUserUseCase:
    def __init__(self, users: UserRepository, token_service: TokenService) -> None:
        self._users = users
        self._token_service = token_service

    def execute(self, token: str) -> UserDTO:
        claims = self._token_service.decode(token)
        user = self._users.get_by_id(claims.user_id)
        if user is None:
            raise InvalidTokenError()
        return UserDTO.from_entity(user)
