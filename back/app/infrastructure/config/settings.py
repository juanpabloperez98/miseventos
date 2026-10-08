import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum

from dotenv import load_dotenv

MIN_JWT_SECRET_LENGTH = 32
LOG_LEVELS = frozenset({"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"})


class ConfigurationError(Exception):
    pass


class Environment(StrEnum):
    DEVELOPMENT = "development"
    TESTING = "testing"


@dataclass(frozen=True, slots=True)
class Settings:
    environment: Environment
    database_url: str = field(repr=False)
    jwt_secret_key: str = field(repr=False)
    jwt_expiration_minutes: int = 60
    cors_origins: tuple[str, ...] = ()
    log_level: str = "INFO"

    def __post_init__(self) -> None:
        if len(self.jwt_secret_key) < MIN_JWT_SECRET_LENGTH:
            raise ConfigurationError(
                f"JWT_SECRET_KEY must be at least {MIN_JWT_SECRET_LENGTH} characters long"
            )
        if self.jwt_expiration_minutes <= 0:
            raise ConfigurationError("JWT_EXPIRATION_MINUTES must be greater than zero")
        if self.log_level not in LOG_LEVELS:
            raise ConfigurationError(f"LOG_LEVEL must be one of {sorted(LOG_LEVELS)}")

    @property
    def debug(self) -> bool:
        return self.environment is Environment.DEVELOPMENT

    @property
    def testing(self) -> bool:
        return self.environment is Environment.TESTING

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> "Settings":
        return cls(
            environment=_parse_environment(env.get("FLASK_ENV", Environment.DEVELOPMENT)),
            database_url=require_env(env, "DATABASE_URL"),
            jwt_secret_key=require_env(env, "JWT_SECRET_KEY"),
            jwt_expiration_minutes=_parse_int(env, "JWT_EXPIRATION_MINUTES", default=60),
            cors_origins=_parse_list(env.get("CORS_ORIGINS", "")),
            log_level=env.get("LOG_LEVEL", "INFO").upper(),
        )


def load_settings() -> Settings:
    load_dotenv()
    return Settings.from_env(os.environ)


def require_env(env: Mapping[str, str], name: str) -> str:
    value = env.get(name, "").strip()
    if not value:
        raise ConfigurationError(f"Environment variable {name} is required")
    return value


def _parse_environment(value: str) -> Environment:
    try:
        return Environment(value.strip().lower())
    except ValueError as error:
        allowed = ", ".join(environment.value for environment in Environment)
        raise ConfigurationError(f"FLASK_ENV must be one of: {allowed}") from error


def _parse_int(env: Mapping[str, str], name: str, default: int) -> int:
    raw_value = env.get(name)
    if raw_value is None or not raw_value.strip():
        return default
    try:
        return int(raw_value)
    except ValueError as error:
        raise ConfigurationError(f"{name} must be an integer") from error


def _parse_list(raw_value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in raw_value.split(",") if item.strip())
