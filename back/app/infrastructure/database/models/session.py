from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.infrastructure.database.models.event import EventModel
    from app.infrastructure.database.models.speaker import SpeakerModel


class SessionModel(TimestampMixin, Base):
    __tablename__ = "sessions"
    __table_args__ = (
        CheckConstraint("capacity > 0", name="capacity_positive"),
        CheckConstraint("end_time > start_time", name="times_ordered"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"), index=True)
    speaker_id: Mapped[int | None] = mapped_column(
        ForeignKey("speakers.id", ondelete="SET NULL"), index=True
    )
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    capacity: Mapped[int]

    event: Mapped["EventModel"] = relationship(back_populates="sessions")
    speaker: Mapped["SpeakerModel | None"] = relationship(back_populates="sessions")
