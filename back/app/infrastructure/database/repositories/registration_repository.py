from sqlalchemy import func, select

from app.domain.entities import Registration
from app.domain.exceptions import AlreadyRegisteredToEventError
from app.domain.ports import RegistrationRepository
from app.infrastructure.database.models import RegistrationModel
from app.infrastructure.database.repositories.base import SqlAlchemyRepository


class SqlAlchemyRegistrationRepository(
    SqlAlchemyRepository[Registration, RegistrationModel], RegistrationRepository
):
    model = RegistrationModel
    entity_name = "Registration"
    unique_violations = {"uq_registrations_user_id_event_id": AlreadyRegisteredToEventError}

    def get(self, user_id: int, event_id: int) -> Registration | None:
        model = self._session.scalars(
            select(RegistrationModel).where(
                RegistrationModel.user_id == user_id, RegistrationModel.event_id == event_id
            )
        ).one_or_none()
        return self._to_entity(model) if model is not None else None

    def count_by_event(self, event_id: int) -> int:
        statement = select(func.count()).where(RegistrationModel.event_id == event_id)
        return self._session.scalar(statement) or 0

    def _to_entity(self, model: RegistrationModel) -> Registration:
        return Registration(
            id=model.id,
            user_id=model.user_id,
            event_id=model.event_id,
            registered_at=model.registered_at,
        )

    def _apply(self, entity: Registration, model: RegistrationModel) -> None:
        model.user_id = entity.user_id
        model.event_id = entity.event_id
