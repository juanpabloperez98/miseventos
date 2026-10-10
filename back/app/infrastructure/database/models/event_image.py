from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.infrastructure.database.models.event import EventModel


class EventImageModel(TimestampMixin, Base):
    """Cover image of an event. One per event (`event_id` is unique); deleted with the event."""

    __tablename__ = "event_images"
    __table_args__ = (
        CheckConstraint("width > 0", name="width_positive"),
        CheckConstraint("height > 0", name="height_positive"),
        CheckConstraint("bytes > 0", name="bytes_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"), unique=True)
    public_id: Mapped[str] = mapped_column(String(255), unique=True)
    secure_url: Mapped[str] = mapped_column(String(500))
    width: Mapped[int]
    height: Mapped[int]
    format: Mapped[str] = mapped_column(String(10))
    bytes: Mapped[int]

    event: Mapped["EventModel"] = relationship(back_populates="image")
