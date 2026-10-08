from typing import TYPE_CHECKING

from sqlalchemy import Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.enums import UserRole
from app.infrastructure.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.infrastructure.database.models.event import EventModel
    from app.infrastructure.database.models.registration import RegistrationModel


class UserModel(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", native_enum=False, create_constraint=True, length=20)
    )

    created_events: Mapped[list["EventModel"]] = relationship(back_populates="creator")
    registrations: Mapped[list["RegistrationModel"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
