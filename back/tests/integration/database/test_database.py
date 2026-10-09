from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import Connection, Engine, inspect, text

EXPECTED_TABLES = {"users", "events", "registrations", "speakers", "sessions", "seed_records"}


def test_connects_to_postgresql(connection: Connection) -> None:
    assert connection.scalar(text("SELECT 1")) == 1
    assert connection.dialect.name == "postgresql"


def test_database_is_migrated_to_latest_revision(engine: Engine, alembic_config: Config) -> None:
    head = ScriptDirectory.from_config(alembic_config).get_current_head()

    with engine.connect() as connection:
        current = MigrationContext.configure(connection).get_current_revision()

    assert current == head


def test_schema_contains_expected_tables_and_constraints(engine: Engine) -> None:
    inspector = inspect(engine)

    assert set(inspector.get_table_names()) >= EXPECTED_TABLES
    assert {
        tuple(constraint["column_names"])
        for constraint in inspector.get_unique_constraints("registrations")
    } == {("user_id", "event_id")}
    assert {index["name"] for index in inspector.get_indexes("users") if index["unique"]} == {
        "ix_users_email"
    }
    assert {"ix_events_name", "ix_events_status_start_date"} <= {
        index["name"] for index in inspector.get_indexes("events")
    }
    assert "ix_registrations_event_id" in {
        index["name"] for index in inspector.get_indexes("registrations")
    }
    assert "ix_sessions_event_id" in {index["name"] for index in inspector.get_indexes("sessions")}
