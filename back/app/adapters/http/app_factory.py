from flask import Flask
from flask_cors import CORS

from app.adapters.cli import seed_initial_data_command
from app.adapters.http.dependencies import CONTAINER_EXTENSION_KEY, close_request_scope
from app.adapters.http.error_handlers import register_error_handlers
from app.adapters.http.middleware import register_request_logging
from app.adapters.http.openapi import create_api
from app.adapters.http.routes import BLUEPRINTS
from app.container import Container


def create_flask_app(container: Container) -> Flask:
    settings = container.settings
    app = Flask("app")
    app.config.update(TESTING=settings.testing)
    app.extensions[CONTAINER_EXTENSION_KEY] = container

    CORS(app, resources={r"/api/*": {"origins": list(settings.cors_origins)}})

    api = create_api(app)
    for blueprint in BLUEPRINTS:
        api.register_blueprint(blueprint)

    register_error_handlers(app)
    register_request_logging(app)
    app.teardown_appcontext(close_request_scope)
    app.cli.add_command(seed_initial_data_command)
    return app
