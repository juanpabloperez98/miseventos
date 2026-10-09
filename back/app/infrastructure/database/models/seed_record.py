from sqlalchemy import Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.ports import SeedEntityType
from app.infrastructure.database.base import Base, TimestampMixin


class SeedRecordModel(TimestampMixin, Base):
    """Bookkeeping for the initial data seeder; not part of the business model."""

    __tablename__ = "seed_records"

    seed_key: Mapped[str] = mapped_column(String(150), primary_key=True)
    entity_type: Mapped[SeedEntityType] = mapped_column(
        Enum(
            SeedEntityType,
            name="seed_entity_type",
            native_enum=False,
            create_constraint=True,
            length=20,
        )
    )
    entity_id: Mapped[int]
