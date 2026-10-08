from sqlalchemy import select

from app.domain.entities import Session
from app.domain.ports import SessionRepository
from app.infrastructure.database.models import SessionModel
from app.infrastructure.database.repositories.base import SqlAlchemyRepository


class SqlAlchemySessionRepository(SqlAlchemyRepository[Session, SessionModel], SessionRepository):
    model = SessionModel
    entity_name = "Session"

    def list_by_event(self, event_id: int) -> list[Session]:
        statement = (
            select(SessionModel)
            .where(SessionModel.event_id == event_id)
            .order_by(SessionModel.start_time, SessionModel.id)
        )
        return [self._to_entity(model) for model in self._session.scalars(statement)]

    def _to_entity(self, model: SessionModel) -> Session:
        return Session(
            id=model.id,
            event_id=model.event_id,
            speaker_id=model.speaker_id,
            title=model.title,
            description=model.description,
            start_time=model.start_time,
            end_time=model.end_time,
            capacity=model.capacity,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _apply(self, entity: Session, model: SessionModel) -> None:
        model.event_id = entity.event_id
        model.speaker_id = entity.speaker_id
        model.title = entity.title
        model.description = entity.description
        model.start_time = entity.start_time
        model.end_time = entity.end_time
        model.capacity = entity.capacity
