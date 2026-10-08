from http import HTTPStatus
from typing import Any

from flask_smorest import Blueprint

from app.adapters.http.dependencies import request_scope
from app.adapters.http.middleware import authenticated, current_user
from app.adapters.http.openapi import BEARER_SECURITY
from app.adapters.http.schemas.auth import (
    AccessTokenSchema,
    LoginRequestSchema,
    RegisterRequestSchema,
    UserSchema,
)
from app.adapters.http.schemas.common import ErrorSchema
from app.application.dto import LoginCommand, RegisterUserCommand, UserDTO
from app.domain.ports import AccessToken

blueprint = Blueprint(
    "auth", __name__, url_prefix="/api/auth", description="Registration and authentication"
)


@blueprint.route("/register", methods=["POST"])
@blueprint.arguments(RegisterRequestSchema)
@blueprint.response(HTTPStatus.CREATED, UserSchema)
@blueprint.alt_response(
    HTTPStatus.CONFLICT, schema=ErrorSchema, description="Email already registered"
)
def register(payload: dict[str, Any]) -> UserDTO:
    return request_scope().register_user().execute(RegisterUserCommand(**payload))


@blueprint.route("/login", methods=["POST"])
@blueprint.arguments(LoginRequestSchema)
@blueprint.response(HTTPStatus.OK, AccessTokenSchema)
@blueprint.alt_response(
    HTTPStatus.UNAUTHORIZED, schema=ErrorSchema, description="Invalid credentials"
)
def login(payload: dict[str, Any]) -> AccessToken:
    return request_scope().login_user().execute(LoginCommand(**payload))


@blueprint.route("/me")
@blueprint.doc(security=BEARER_SECURITY)
@blueprint.response(HTTPStatus.OK, UserSchema)
@blueprint.alt_response(
    HTTPStatus.UNAUTHORIZED, schema=ErrorSchema, description="Missing or invalid token"
)
@authenticated
def me() -> UserDTO:
    return current_user()
