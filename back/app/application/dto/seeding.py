from dataclasses import dataclass, field

from app.domain.enums import UserRole


@dataclass(frozen=True, slots=True)
class SeedUser:
    name: str
    email: str
    password: str = field(repr=False)
    role: UserRole


@dataclass(frozen=True, slots=True)
class SeedInitialDataCommand:
    users: tuple[SeedUser, ...] = ()
    demo_data: bool = False

    @property
    def organizer(self) -> SeedUser | None:
        return next((user for user in self.users if user.role is UserRole.ORGANIZER), None)


@dataclass(slots=True)
class SeedReport:
    users_created: int = 0
    users_existing: int = 0
    records_created: int = 0
    records_existing: int = 0
    records_skipped: int = 0
    demo_data_skipped: bool = False
