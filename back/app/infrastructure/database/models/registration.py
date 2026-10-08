from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.base import Base

if TYPE_CHECKING:
    from app.infrastructure.database.models.event import EventModel
    from app.infrastructure.database.models.user import UserModel


class RegistrationModel(Base):
    __tablename__ = "registrations"
    # The (user_id, event_id) unique index also serves lookups by user_id.
    __table_args__ = (UniqueConstraint("user_id", "event_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"), index=True)
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user: Mapped["UserModel"] = relationship(back_populates="registrations")
    event: Mapped["EventModel"] = relationship(back_populates="registrations")
