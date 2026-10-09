import pytest

from app.infrastructure.config import ConfigurationError, Environment, Settings

VALID_ENV = {
    "FLASK_ENV": "development",
    "DATABASE_URL": "postgresql+psycopg://user:pass@postgres:5432/miseventos",
    "JWT_SECRET_KEY": "a-very-long-secret-key-used-only-in-tests",
    "JWT_EXPIRATION_MINUTES": "30",
    "CORS_ORIGINS": "http://localhost:4200, http://127.0.0.1:4200 ,",
    "LOG_LEVEL": "debug",
}


def test_reads_all_values_from_environment() -> None:
    settings = Settings.from_env(VALID_ENV)

    assert settings.environment is Environment.DEVELOPMENT
    assert settings.debug
    assert not settings.testing
    assert settings.database_url == VALID_ENV["DATABASE_URL"]
    assert settings.jwt_expiration_minutes == 30
    assert settings.cors_origins == ("http://localhost:4200", "http://127.0.0.1:4200")
    assert settings.log_level == "DEBUG"


def test_applies_defaults_for_optional_values() -> None:
    env = {"DATABASE_URL": VALID_ENV["DATABASE_URL"], "JWT_SECRET_KEY": VALID_ENV["JWT_SECRET_KEY"]}

    settings = Settings.from_env(env)

    assert settings.environment is Environment.DEVELOPMENT
    assert settings.jwt_expiration_minutes == 60
    assert settings.cors_origins == ()
    assert settings.log_level == "INFO"


@pytest.mark.parametrize("missing", ["DATABASE_URL", "JWT_SECRET_KEY"])
def test_requires_mandatory_variables(missing: str) -> None:
    env = {key: value for key, value in VALID_ENV.items() if key != missing}

    with pytest.raises(ConfigurationError, match=missing):
        Settings.from_env(env)


@pytest.mark.parametrize(
    ("key", "value", "message"),
    [
        ("JWT_SECRET_KEY", "too-short", "at least 32"),
        ("JWT_EXPIRATION_MINUTES", "0", "greater than zero"),
        ("JWT_EXPIRATION_MINUTES", "soon", "integer"),
        ("FLASK_ENV", "staging", "FLASK_ENV"),
        ("LOG_LEVEL", "verbose", "LOG_LEVEL"),
    ],
)
def test_rejects_invalid_values(key: str, value: str, message: str) -> None:
    with pytest.raises(ConfigurationError, match=message):
        Settings.from_env({**VALID_ENV, key: value})


def test_reads_production_environment() -> None:
    settings = Settings.from_env({**VALID_ENV, "FLASK_ENV": "production"})

    assert settings.environment is Environment.PRODUCTION
    assert not settings.debug
    assert not settings.testing


def test_repr_does_not_leak_secrets() -> None:
    settings = Settings.from_env(VALID_ENV)

    assert VALID_ENV["JWT_SECRET_KEY"] not in repr(settings)
    assert "pass@" not in repr(settings)
