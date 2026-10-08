from sqlalchemy import select

from app.domain.entities import User
from app.domain.exceptions import EmailAlreadyRegisteredError
from app.domain.ports import UserRepository
from app.infrastructure.database.models import UserModel
from app.infrastructure.database.repositories.base import SqlAlchemyRepository


class SqlAlchemyUserRepository(SqlAlchemyRepository[User, UserModel], UserRepository):
    model = UserModel
    entity_name = "User"
    unique_violations = {"ix_users_email": EmailAlreadyRegisteredError}

    def get_by_email(self, email: str) -> User | None:
        model = self._session.scalars(
            select(UserModel).where(UserModel.email == email)
        ).one_or_none()
        return self._to_entity(model) if model is not None else None

    def _to_entity(self, model: UserModel) -> User:
        return User(
            id=model.id,
            name=model.name,
            email=model.email,
            password_hash=model.password_hash,
            role=model.role,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _apply(self, entity: User, model: UserModel) -> None:
        model.name = entity.name
        model.email = entity.email
        model.password_hash = entity.password_hash
        model.role = entity.role
