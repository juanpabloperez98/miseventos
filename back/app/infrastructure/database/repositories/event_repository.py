from sqlalchemy import or_, select

from app.domain.entities import Event
from app.domain.ports import EventRepository, EventSearchCriteria
from app.domain.value_objects import Page, PageRequest
from app.infrastructure.database.models import EventModel, RegistrationModel
from app.infrastructure.database.repositories.base import SqlAlchemyRepository


class SqlAlchemyEventRepository(SqlAlchemyRepository[Event, EventModel], EventRepository):
    model = EventModel
    entity_name = "Event"

    def get_by_id_for_update(self, event_id: int) -> Event | None:
        statement = (
            select(EventModel)
            .where(EventModel.id == event_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        model = self._session.scalars(statement).one_or_none()
        return self._to_entity(model) if model is not None else None

    def search(self, criteria: EventSearchCriteria, page: PageRequest) -> Page[Event]:
        statement = select(EventModel)
        if criteria.text:
            statement = statement.where(
                or_(
                    EventModel.name.icontains(criteria.text, autoescape=True),
                    EventModel.description.icontains(criteria.text, autoescape=True),
                    EventModel.location.icontains(criteria.text, autoescape=True),
                )
            )
        if criteria.status is not None:
            statement = statement.where(EventModel.status == criteria.status)
        return self._paginate(statement.order_by(EventModel.start_date, EventModel.id), page)

    def list_by_attendee(self, user_id: int) -> list[Event]:
        statement = (
            select(EventModel)
            .join(RegistrationModel, RegistrationModel.event_id == EventModel.id)
            .where(RegistrationModel.user_id == user_id)
            .order_by(EventModel.start_date, EventModel.id)
        )
        return [self._to_entity(model) for model in self._session.scalars(statement)]

    def _to_entity(self, model: EventModel) -> Event:
        return Event(
            id=model.id,
            name=model.name,
            description=model.description,
            location=model.location,
            start_date=model.start_date,
            end_date=model.end_date,
            capacity=model.capacity,
            status=model.status,
            created_by=model.created_by,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _apply(self, entity: Event, model: EventModel) -> None:
        model.name = entity.name
        model.description = entity.description
        model.location = entity.location
        model.start_date = entity.start_date
        model.end_date = entity.end_date
        model.capacity = entity.capacity
        model.status = entity.status
        model.created_by = entity.created_by
