from sqlalchemy import select

from app.domain.entities import Speaker
from app.domain.ports import SpeakerRepository
from app.domain.value_objects import Page, PageRequest
from app.infrastructure.database.models import SpeakerModel
from app.infrastructure.database.repositories.base import SqlAlchemyRepository


class SqlAlchemySpeakerRepository(SqlAlchemyRepository[Speaker, SpeakerModel], SpeakerRepository):
    model = SpeakerModel
    entity_name = "Speaker"

    def list_all(self, page: PageRequest) -> Page[Speaker]:
        return self._paginate(
            select(SpeakerModel).order_by(SpeakerModel.name, SpeakerModel.id), page
        )

    def _to_entity(self, model: SpeakerModel) -> Speaker:
        return Speaker(
            id=model.id,
            name=model.name,
            bio=model.bio,
            email=model.email,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _apply(self, entity: Speaker, model: SpeakerModel) -> None:
        model.name = entity.name
        model.bio = entity.bio
        model.email = entity.email
