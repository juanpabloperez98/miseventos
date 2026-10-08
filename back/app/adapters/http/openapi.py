from typing import Any

from flask import Flask
from flask.typing import ResponseReturnValue
from flask_smorest import Api
from werkzeug.exceptions import HTTPException

from app.adapters.http.schemas.common import ErrorSchema

BEARER_SCHEME_NAME = "bearerAuth"
BEARER_SECURITY: list[dict[str, list[str]]] = [{BEARER_SCHEME_NAME: []}]

OPENAPI_CONFIG: dict[str, Any] = {
    "API_TITLE": "Mis Eventos API",
    "API_VERSION": "v1",
    "OPENAPI_VERSION": "3.0.3",
    "OPENAPI_URL_PREFIX": "/",
    "OPENAPI_JSON_PATH": "openapi.json",
    "OPENAPI_SWAGGER_UI_PATH": "/docs",
    "OPENAPI_SWAGGER_UI_URL": "https://cdn.jsdelivr.net/npm/swagger-ui-dist/",
    "API_SPEC_OPTIONS": {
        "info": {"description": "REST API for managing events, sessions, speakers and attendees."}
    },
}


class RestApi(Api):  # type: ignore[misc]
    ERROR_SCHEMA = ErrorSchema

    def handle_http_exception(self, error: HTTPException) -> ResponseReturnValue:
        data: dict[str, Any] = getattr(error, "data", None) or {}
        errors = data.get("errors") or data.get("messages")
        message = data.get("message") or (
            "Request validation failed" if errors else error.description
        )
        payload: dict[str, Any] = {"message": message}
        if errors:
            payload["errors"] = errors
        return payload, error.code or 500, data.get("headers", {})


def create_api(app: Flask) -> RestApi:
    app.config.update(OPENAPI_CONFIG)
    api = RestApi(app)
    api.spec.components.security_scheme(
        BEARER_SCHEME_NAME, {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
    )
    return api
