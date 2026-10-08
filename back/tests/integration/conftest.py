import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from flask import Flask
from flask.testing import FlaskClient
from sqlalchemy import Connection, Engine, create_engine, make_url, text
from sqlalchemy.orm import Session, sessionmaker

from app.bootstrap import create_app
from app.container import Container
from app.infrastructure.config import Settings
from app.infrastructure.database.session import create_database_engine

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def _ensure_database_exists(database_url: str) -> None:
    url = make_url(database_url)
    maintenance_engine = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with maintenance_engine.connect() as connection:
        exists = connection.scalar(
            text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": url.database}
        )
        if not exists:
            connection.execute(text(f'CREATE DATABASE "{url.database}"'))
    maintenance_engine.dispose()


def _alembic_config(database_url: str) -> Config:
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.attributes["database_url"] = database_url
    config.attributes["configure_logger"] = False
    return config


@pytest.fixture(scope="session")
def database_url() -> str:
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL is not set")
    database_name = make_url(url).database or ""
    if not database_name.endswith("_test"):
        pytest.fail("TEST_DATABASE_URL must point to a database whose name ends with '_test'")
    _ensure_database_exists(url)
    return url


@pytest.fixture(scope="session")
def alembic_config(database_url: str) -> Config:
    return _alembic_config(database_url)


@pytest.fixture(scope="session")
def engine(database_url: str, alembic_config: Config) -> Iterator[Engine]:
    command.upgrade(alembic_config, "head")
    database_engine = create_database_engine(database_url)
    yield database_engine
    database_engine.dispose()
    command.downgrade(alembic_config, "base")


@pytest.fixture
def connection(engine: Engine) -> Iterator[Connection]:
    with engine.connect() as database_connection:
        transaction = database_connection.begin()
        yield database_connection
        transaction.rollback()


@pytest.fixture
def session_factory(connection: Connection) -> sessionmaker[Session]:
    return sessionmaker(
        bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False
    )


@pytest.fixture
def db_session(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    session = session_factory()
    yield session
    session.close()


@pytest.fixture
def db_app(settings: Settings, session_factory: sessionmaker[Session]) -> Flask:
    app = create_app(settings)
    container: Container = app.extensions["container"]
    container.session_factory = session_factory
    return app


@pytest.fixture
def db_client(db_app: Flask) -> FlaskClient:
    return db_app.test_client()
