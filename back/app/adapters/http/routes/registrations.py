from http import HTTPStatus
from typing import Any

from flask_smorest import Blueprint

from app.adapters.http.dependencies import request_scope
from app.adapters.http.middleware import authenticated, current_actor
from app.adapters.http.openapi import BEARER_SECURITY
from app.adapters.http.schemas.common import MAX_DATABASE_ID, ErrorSchema
from app.adapters.http.schemas.events import EventSchema
from app.adapters.http.schemas.registrations import (
    RegistrationRequestSchema,
    RegistrationSchema,
)
from app.domain.entities import Event, Registration

blueprint = Blueprint(
    "registrations", __name__, url_prefix="/api", description="Event registrations"
)


@blueprint.route(f"/events/<int(max={MAX_DATABASE_ID}):event_id>/registrations", methods=["POST"])
@authenticated
@blueprint.doc(
    security=BEARER_SECURITY,
    description="Registers the authenticated user to a published event with free capacity. "
    "The user is always taken from the token; the request body must be empty.",
)
@blueprint.arguments(RegistrationRequestSchema, required=False)
@blueprint.response(HTTPStatus.CREATED, RegistrationSchema)
@blueprint.alt_response(HTTPStatus.UNAUTHORIZED, schema=ErrorSchema, description="Bad token")
@blueprint.alt_response(HTTPStatus.NOT_FOUND, schema=ErrorSchema, description="Event not found")
@blueprint.alt_response(
    HTTPStatus.CONFLICT,
    schema=ErrorSchema,
    description="Already registered, event full or not open for registration",
)
def register_for_event(_payload: dict[str, Any], event_id: int) -> Registration:
    return request_scope().register_for_event().execute(current_actor(), event_id)


@blueprint.route("/me/registrations")
@authenticated
@blueprint.doc(
    security=BEARER_SECURITY,
    description="Events the authenticated user is registered to, including events that were "
    "later cancelled or completed.",
)
@blueprint.response(HTTPStatus.OK, EventSchema(many=True))
@blueprint.alt_response(HTTPStatus.UNAUTHORIZED, schema=ErrorSchema, description="Bad token")
def list_my_registered_events() -> list[Event]:
    return request_scope().list_my_registered_events().execute(current_actor())
