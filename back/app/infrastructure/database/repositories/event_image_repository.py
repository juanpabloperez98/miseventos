from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.domain.entities import EventImage
from app.domain.ports import EventImageRepository
from app.infrastructure.database.models import EventImageModel


class SqlAlchemyEventImageRepository(EventImageRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_event(self, event_id: int) -> EventImage | None:
        model = self._find(event_id)
        return to_event_image(model) if model is not None else None

    def save(self, image: EventImage) -> EventImage:
        model = self._find(image.event_id)
        if model is None:
            model = EventImageModel(event_id=image.event_id)
            self._session.add(model)
        model.public_id = image.public_id
        model.secure_url = image.secure_url
        model.width = image.width
        model.height = image.height
        model.format = image.format
        model.bytes = image.bytes
        self._session.flush()
        return to_event_image(model)

    def delete_by_event(self, event_id: int) -> None:
        self._session.execute(delete(EventImageModel).where(EventImageModel.event_id == event_id))
        self._session.flush()

    def _find(self, event_id: int) -> EventImageModel | None:
        statement = (
            select(EventImageModel)
            .where(EventImageModel.event_id == event_id)
            .execution_options(populate_existing=True)
        )
        return self._session.scalars(statement).one_or_none()


def to_event_image(model: EventImageModel) -> EventImage:
    return EventImage(
        id=model.id,
        event_id=model.event_id,
        public_id=model.public_id,
        secure_url=model.secure_url,
        width=model.width,
        height=model.height,
        format=model.format,
        bytes=model.bytes,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )
