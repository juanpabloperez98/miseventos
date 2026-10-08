from typing import TYPE_CHECKING

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.infrastructure.database.models.session import SessionModel


class SpeakerModel(TimestampMixin, Base):
    __tablename__ = "speakers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    bio: Mapped[str | None] = mapped_column(Text)
    email: Mapped[str | None] = mapped_column(String(255))

    sessions: Mapped[list["SessionModel"]] = relationship(
        back_populates="speaker", passive_deletes=True
    )
