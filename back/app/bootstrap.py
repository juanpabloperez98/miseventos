from flask import Flask

from app.adapters.http.app_factory import create_flask_app
from app.container import Container
from app.infrastructure.config import Settings, load_settings
from app.infrastructure.logging_config import configure_logging


def create_app(settings: Settings | None = None) -> Flask:
    resolved_settings = settings or load_settings()
    configure_logging(resolved_settings.log_level)
    return create_flask_app(Container(resolved_settings))
