import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum

from dotenv import load_dotenv

MIN_JWT_SECRET_LENGTH = 32
# Production also rejects low-variety keys ("aaaa...", "1234...") and documented placeholders.
MIN_PRODUCTION_JWT_SECRET_DISTINCT_CHARS = 16
JWT_SECRET_PLACEHOLDER_MARKERS = ("replace-with", "change-me", "changeme")
LOG_LEVELS = frozenset({"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"})
SEED_ENABLED_VARIABLES = (
    "SEED_ADMIN_ENABLED",
    "SEED_ORGANIZER_ENABLED",
    "SEED_ATTENDEE_ENABLED",
    "SEED_DEMO_DATA_ENABLED",
)

DEFAULT_EVENT_IMAGE_MAX_BYTES = 5 * 1024 * 1024
CLOUDINARY_VARIABLES = ("CLOUDINARY_CLOUD_NAME", "CLOUDINARY_API_KEY", "CLOUDINARY_API_SECRET")

_TRUE_VALUES = frozenset({"1", "true", "yes", "on"})
_FALSE_VALUES = frozenset({"0", "false", "no", "off", ""})


class ConfigurationError(Exception):
    pass


class Environment(StrEnum):
    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"


@dataclass(frozen=True, slots=True)
class Settings:
    environment: Environment
    database_url: str = field(repr=False)
    jwt_secret_key: str = field(repr=False)
    jwt_expiration_minutes: int = 60
    cors_origins: tuple[str, ...] = ()
    log_level: str = "INFO"
    # Cloudinary (optional): without these three values image uploads answer 503.
    cloudinary_cloud_name: str = ""
    cloudinary_api_key: str = ""
    cloudinary_api_secret: str = field(default="", repr=False)
    cloudinary_folder: str = "mis-eventos"
    event_image_max_bytes: int = DEFAULT_EVENT_IMAGE_MAX_BYTES

    def __post_init__(self) -> None:
        if len(self.jwt_secret_key) < MIN_JWT_SECRET_LENGTH:
            raise ConfigurationError(
                f"JWT_SECRET_KEY must be at least {MIN_JWT_SECRET_LENGTH} characters long"
            )
        if self.jwt_expiration_minutes <= 0:
            raise ConfigurationError("JWT_EXPIRATION_MINUTES must be greater than zero")
        if self.log_level not in LOG_LEVELS:
            raise ConfigurationError(f"LOG_LEVEL must be one of {sorted(LOG_LEVELS)}")
        if self.environment is Environment.PRODUCTION:
            _ensure_production_jwt_secret(self.jwt_secret_key)
        credentials = (
            self.cloudinary_cloud_name,
            self.cloudinary_api_key,
            self.cloudinary_api_secret,
        )
        if any(credentials) and not all(credentials):
            raise ConfigurationError(
                f"Set all of {', '.join(CLOUDINARY_VARIABLES)} or none of them"
            )
        if self.event_image_max_bytes <= 0:
            raise ConfigurationError("EVENT_IMAGE_MAX_BYTES must be greater than zero")

    @property
    def cloudinary_enabled(self) -> bool:
        return bool(self.cloudinary_cloud_name)

    @property
    def debug(self) -> bool:
        return self.environment is Environment.DEVELOPMENT

    @property
    def testing(self) -> bool:
        return self.environment is Environment.TESTING

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> "Settings":
        environment = _parse_environment(env.get("FLASK_ENV", Environment.DEVELOPMENT))
        if environment is Environment.PRODUCTION:
            _ensure_seeding_disabled(env)
        return cls(
            environment=environment,
            database_url=require_env(env, "DATABASE_URL"),
            jwt_secret_key=require_env(env, "JWT_SECRET_KEY"),
            jwt_expiration_minutes=_parse_int(env, "JWT_EXPIRATION_MINUTES", default=60),
            cors_origins=_parse_list(env.get("CORS_ORIGINS", "")),
            log_level=env.get("LOG_LEVEL", "INFO").upper(),
            cloudinary_cloud_name=env.get("CLOUDINARY_CLOUD_NAME", "").strip(),
            cloudinary_api_key=env.get("CLOUDINARY_API_KEY", "").strip(),
            cloudinary_api_secret=env.get("CLOUDINARY_API_SECRET", "").strip(),
            cloudinary_folder=env.get("CLOUDINARY_FOLDER", "").strip() or "mis-eventos",
            event_image_max_bytes=_parse_int(
                env, "EVENT_IMAGE_MAX_BYTES", default=DEFAULT_EVENT_IMAGE_MAX_BYTES
            ),
        )


def load_settings() -> Settings:
    load_dotenv()
    return Settings.from_env(os.environ)


def require_env(env: Mapping[str, str], name: str) -> str:
    value = env.get(name, "").strip()
    if not value:
        raise ConfigurationError(f"Environment variable {name} is required")
    return value


def parse_bool(env: Mapping[str, str], name: str) -> bool:
    value = env.get(name, "").strip().lower()
    if value in _TRUE_VALUES:
        return True
    if value in _FALSE_VALUES:
        return False
    raise ConfigurationError(f"{name} must be true or false")


def _ensure_production_jwt_secret(secret: str) -> None:
    # Messages never include the secret itself.
    lowered = secret.lower()
    if any(marker in lowered for marker in JWT_SECRET_PLACEHOLDER_MARKERS):
        raise ConfigurationError(
            "JWT_SECRET_KEY still contains a placeholder value; set a random secret for production"
        )
    if len(set(secret)) < MIN_PRODUCTION_JWT_SECRET_DISTINCT_CHARS:
        raise ConfigurationError(
            "JWT_SECRET_KEY is too predictable for production; generate it with "
            "secrets.token_urlsafe(48)"
        )


def _ensure_seeding_disabled(env: Mapping[str, str]) -> None:
    enabled = [name for name in SEED_ENABLED_VARIABLES if parse_bool(env, name)]
    if enabled:
        raise ConfigurationError(
            f"Seeding must be disabled in production; set to false: {', '.join(enabled)}"
        )


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
