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


PRODUCTION_ENV = {
    **VALID_ENV,
    "FLASK_ENV": "production",
    "JWT_SECRET_KEY": "Zq3vL8xK2pR7tW1nY6bH4mC9jD5fG0sA",
}


@pytest.mark.parametrize(
    "secret",
    [
        "replace-with-a-long-random-secret-of-at-least-32-chars",
        "CHANGE-ME-CHANGE-ME-CHANGE-ME-CHANGE-ME",
        "changeme-0123456789abcdefghijklmnop",
    ],
)
def test_production_rejects_placeholder_jwt_secrets(secret: str) -> None:
    with pytest.raises(ConfigurationError, match="placeholder") as error:
        Settings.from_env({**PRODUCTION_ENV, "JWT_SECRET_KEY": secret})

    assert secret not in str(error.value)


@pytest.mark.parametrize("secret", ["a" * 64, "0123456789" * 4])
def test_production_rejects_predictable_jwt_secrets(secret: str) -> None:
    with pytest.raises(ConfigurationError, match="too predictable") as error:
        Settings.from_env({**PRODUCTION_ENV, "JWT_SECRET_KEY": secret})

    assert secret not in str(error.value)


def test_production_accepts_a_random_jwt_secret() -> None:
    settings = Settings.from_env(PRODUCTION_ENV)

    assert settings.environment is Environment.PRODUCTION


def test_development_keeps_the_basic_jwt_rules() -> None:
    placeholder = "replace-with-a-long-random-secret-of-at-least-32-chars"

    settings = Settings.from_env({**VALID_ENV, "JWT_SECRET_KEY": placeholder})

    assert settings.environment is Environment.DEVELOPMENT


@pytest.mark.parametrize(
    "variable",
    [
        "SEED_ADMIN_ENABLED",
        "SEED_ORGANIZER_ENABLED",
        "SEED_ATTENDEE_ENABLED",
        "SEED_DEMO_DATA_ENABLED",
    ],
)
def test_production_refuses_enabled_seeders(variable: str) -> None:
    with pytest.raises(ConfigurationError, match=f"Seeding must be disabled.*{variable}"):
        Settings.from_env({**PRODUCTION_ENV, variable: "true"})


def test_production_accepts_explicitly_disabled_seeders() -> None:
    env = {
        **PRODUCTION_ENV,
        "SEED_ADMIN_ENABLED": "false",
        "SEED_ORGANIZER_ENABLED": "0",
        "SEED_ATTENDEE_ENABLED": "no",
        "SEED_DEMO_DATA_ENABLED": "",
    }

    assert Settings.from_env(env).environment is Environment.PRODUCTION


def test_production_rejects_ambiguous_seed_flags() -> None:
    with pytest.raises(ConfigurationError, match="SEED_ADMIN_ENABLED must be true or false"):
        Settings.from_env({**PRODUCTION_ENV, "SEED_ADMIN_ENABLED": "maybe"})


def test_development_allows_seeders() -> None:
    settings = Settings.from_env({**VALID_ENV, "SEED_ADMIN_ENABLED": "true"})

    assert settings.environment is Environment.DEVELOPMENT
