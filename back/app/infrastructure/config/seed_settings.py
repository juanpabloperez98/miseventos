import os
from collections.abc import Mapping
from dataclasses import dataclass

from dotenv import load_dotenv

from app.application.dto import SeedInitialDataCommand, SeedUser
from app.domain.enums import UserRole
from app.domain.exceptions import InvalidValueError
from app.domain.value_objects import Email
from app.infrastructure.config.settings import ConfigurationError, parse_bool, require_env

# Same limits the public registration endpoint applies to passwords.
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128


@dataclass(frozen=True, slots=True)
class SeedSettings:
    """Seeder configuration. Every seed is disabled unless explicitly enabled."""

    users: tuple[SeedUser, ...] = ()
    demo_data_enabled: bool = False

    def __post_init__(self) -> None:
        emails = [user.email for user in self.users]
        if len(emails) != len(set(emails)):
            raise ConfigurationError("Seed users must use different emails")
        has_organizer = any(user.role is UserRole.ORGANIZER for user in self.users)
        if self.demo_data_enabled and not has_organizer:
            raise ConfigurationError("SEED_DEMO_DATA_ENABLED requires SEED_ORGANIZER_ENABLED=true")

    def to_command(self) -> SeedInitialDataCommand:
        return SeedInitialDataCommand(users=self.users, demo_data=self.demo_data_enabled)

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> "SeedSettings":
        users = tuple(
            _parse_user(env, role)
            for role in UserRole
            if parse_bool(env, f"SEED_{role.value}_ENABLED")
        )
        return cls(users=users, demo_data_enabled=parse_bool(env, "SEED_DEMO_DATA_ENABLED"))


def load_seed_settings() -> SeedSettings:
    load_dotenv()
    return SeedSettings.from_env(os.environ)


def _parse_user(env: Mapping[str, str], role: UserRole) -> SeedUser:
    prefix = f"SEED_{role.value}"
    try:
        email = Email(require_env(env, f"{prefix}_EMAIL")).value
    except InvalidValueError as error:
        raise ConfigurationError(f"{prefix}_EMAIL must be a valid email address") from error

    password = env.get(f"{prefix}_PASSWORD", "")
    if not MIN_PASSWORD_LENGTH <= len(password) <= MAX_PASSWORD_LENGTH:
        raise ConfigurationError(
            f"{prefix}_PASSWORD must be between {MIN_PASSWORD_LENGTH} and "
            f"{MAX_PASSWORD_LENGTH} characters long"
        )
    return SeedUser(
        name=require_env(env, f"{prefix}_NAME"), email=email, password=password, role=role
    )
