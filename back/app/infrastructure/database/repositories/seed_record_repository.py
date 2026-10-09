from sqlalchemy.orm import Session

from app.domain.ports import SeedRecord, SeedRecordRepository
from app.infrastructure.database.models import SeedRecordModel


class SqlAlchemySeedRecordRepository(SeedRecordRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, seed_key: str) -> SeedRecord | None:
        model = self._session.get(SeedRecordModel, seed_key)
        if model is None:
            return None
        return SeedRecord(model.seed_key, model.entity_type, model.entity_id)

    def save(self, record: SeedRecord) -> None:
        model = self._session.get(SeedRecordModel, record.seed_key)
        if model is None:
            model = SeedRecordModel(seed_key=record.seed_key)
            self._session.add(model)
        model.entity_type = record.entity_type
        model.entity_id = record.entity_id
        self._session.flush()
