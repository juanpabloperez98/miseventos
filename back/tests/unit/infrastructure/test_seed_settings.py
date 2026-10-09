import pytest

from app.domain.enums import UserRole
from app.infrastructure.config import ConfigurationError, SeedSettings

ENABLED_ENV = {
    "SEED_ADMIN_ENABLED": "true",
    "SEED_ADMIN_NAME": "Admin Mis Eventos",
    "SEED_ADMIN_EMAIL": " Admin@Example.com ",
    "SEED_ADMIN_PASSWORD": "admin-password",
    "SEED_ORGANIZER_ENABLED": "TRUE",
    "SEED_ORGANIZER_NAME": "Organizer Mis Eventos",
    "SEED_ORGANIZER_EMAIL": "organizer@example.com",
    "SEED_ORGANIZER_PASSWORD": "organizer-password",
    "SEED_ATTENDEE_ENABLED": "1",
    "SEED_ATTENDEE_NAME": "Attendee Mis Eventos",
    "SEED_ATTENDEE_EMAIL": "attendee@example.com",
    "SEED_ATTENDEE_PASSWORD": "attendee-password",
    "SEED_DEMO_DATA_ENABLED": "yes",
}


def test_reads_enabled_users_and_demo_data() -> None:
    settings = SeedSettings.from_env(ENABLED_ENV)

    assert [user.role for user in settings.users] == [
        UserRole.ADMIN,
        UserRole.ORGANIZER,
        UserRole.ATTENDEE,
    ]
    assert settings.users[0].email == "admin@example.com"
    assert settings.demo_data_enabled
    command = settings.to_command()
    assert command.demo_data
    assert command.organizer == settings.users[1]


def test_every_seed_is_disabled_by_default() -> None:
    settings = SeedSettings.from_env({})

    assert settings.users == ()
    assert not settings.demo_data_enabled


def test_disabled_users_do_not_require_credentials() -> None:
    settings = SeedSettings.from_env(
        {**ENABLED_ENV, "SEED_ADMIN_ENABLED": "false", "SEED_ADMIN_PASSWORD": ""}
    )

    assert UserRole.ADMIN not in {user.role for user in settings.users}


@pytest.mark.parametrize(
    ("key", "value", "message"),
    [
        ("SEED_ADMIN_ENABLED", "maybe", "SEED_ADMIN_ENABLED must be true or false"),
        ("SEED_ADMIN_EMAIL", "", "SEED_ADMIN_EMAIL is required"),
        ("SEED_ADMIN_EMAIL", "not-an-email", "SEED_ADMIN_EMAIL must be a valid email"),
        ("SEED_ADMIN_NAME", " ", "SEED_ADMIN_NAME is required"),
        ("SEED_ADMIN_PASSWORD", "short", "SEED_ADMIN_PASSWORD must be between 8 and 128"),
        ("SEED_ADMIN_PASSWORD", "x" * 129, "SEED_ADMIN_PASSWORD must be between 8 and 128"),
        ("SEED_ATTENDEE_EMAIL", "ADMIN@example.com", "different emails"),
        ("SEED_ORGANIZER_ENABLED", "false", "requires SEED_ORGANIZER_ENABLED"),
    ],
)
def test_rejects_invalid_configuration(key: str, value: str, message: str) -> None:
    with pytest.raises(ConfigurationError, match=message):
        SeedSettings.from_env({**ENABLED_ENV, key: value})


def test_repr_does_not_leak_passwords() -> None:
    settings = SeedSettings.from_env(ENABLED_ENV)

    for key in ("SEED_ADMIN_PASSWORD", "SEED_ORGANIZER_PASSWORD", "SEED_ATTENDEE_PASSWORD"):
        assert ENABLED_ENV[key] not in repr(settings)
