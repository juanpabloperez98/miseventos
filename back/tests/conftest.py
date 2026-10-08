import os

import pytest
from flask import Flask
from flask.testing import FlaskClient

from app.bootstrap import create_app
from app.infrastructure.config import Environment, Settings

TEST_JWT_SECRET = "test-only-jwt-secret-key-with-at-least-32-chars"
UNUSED_DATABASE_URL = "postgresql+psycopg://localhost:5432/miseventos_unused_test"


@pytest.fixture
def settings() -> Settings:
    return Settings(
        environment=Environment.TESTING,
        database_url=os.environ.get("TEST_DATABASE_URL", UNUSED_DATABASE_URL),
        jwt_secret_key=TEST_JWT_SECRET,
        jwt_expiration_minutes=15,
        cors_origins=("http://localhost:4200",),
        log_level="WARNING",
    )


@pytest.fixture
def app(settings: Settings) -> Flask:
    return create_app(settings)


@pytest.fixture
def client(app: Flask) -> FlaskClient:
    return app.test_client()
