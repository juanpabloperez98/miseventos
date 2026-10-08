from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.enums import EventStatus
from app.infrastructure.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.infrastructure.database.models.registration import RegistrationModel
    from app.infrastructure.database.models.session import SessionModel
    from app.infrastructure.database.models.user import UserModel


class EventModel(TimestampMixin, Base):
    __tablename__ = "events"
    __table_args__ = (
        CheckConstraint("capacity > 0", name="capacity_positive"),
        CheckConstraint("end_date > start_date", name="dates_ordered"),
        Index("ix_events_status_start_date", "status", "start_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    location: Mapped[str] = mapped_column(String(255))
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    capacity: Mapped[int]
    status: Mapped[EventStatus] = mapped_column(
        Enum(EventStatus, name="event_status", native_enum=False, create_constraint=True, length=20)
    )
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)

    creator: Mapped["UserModel"] = relationship(back_populates="created_events")
    registrations: Mapped[list["RegistrationModel"]] = relationship(
        back_populates="event", cascade="all, delete-orphan", passive_deletes=True
    )
    sessions: Mapped[list["SessionModel"]] = relationship(
        back_populates="event", cascade="all, delete-orphan", passive_deletes=True
    )
