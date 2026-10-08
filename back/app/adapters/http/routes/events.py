from http import HTTPStatus
from typing import Any

from flask import Response
from flask.views import MethodView
from flask_smorest import Blueprint

from app.adapters.http.dependencies import request_scope
from app.adapters.http.middleware import (
    authenticated,
    current_actor,
    current_actor_or_none,
    optionally_authenticated,
)
from app.adapters.http.openapi import BEARER_SECURITY, OPTIONAL_BEARER_SECURITY
from app.adapters.http.schemas.common import ErrorSchema
from app.adapters.http.schemas.events import (
    EventCreateSchema,
    EventPageSchema,
    EventQuerySchema,
    EventSchema,
    EventUpdateSchema,
)
from app.application.dto import EventDetails, ListEventsQuery, UpdateEventCommand
from app.domain.entities import Event
from app.domain.value_objects import Page

MAX_DATABASE_ID = 2_147_483_647

blueprint = Blueprint("events", __name__, url_prefix="/api/events", description="Events")


@blueprint.route("")
class EventCollection(MethodView):
    @optionally_authenticated
    @blueprint.doc(
        security=OPTIONAL_BEARER_SECURITY,
        description="Anonymous users and attendees only see published events. Organizers also "
        "see their own events and admins see every event.",
    )
    @blueprint.arguments(EventQuerySchema, location="query")
    @blueprint.response(HTTPStatus.OK, EventPageSchema)
    @blueprint.alt_response(HTTPStatus.UNAUTHORIZED, schema=ErrorSchema, description="Bad token")
    def get(self, query: dict[str, Any]) -> Page[Event]:
        return (
            request_scope().list_events().execute(ListEventsQuery(**query), current_actor_or_none())
        )

    @authenticated
    @blueprint.doc(
        security=BEARER_SECURITY, description="Creates a DRAFT event owned by the caller."
    )
    @blueprint.arguments(EventCreateSchema)
    @blueprint.response(HTTPStatus.CREATED, EventSchema)
    @blueprint.alt_response(HTTPStatus.UNAUTHORIZED, schema=ErrorSchema, description="Bad token")
    @blueprint.alt_response(HTTPStatus.FORBIDDEN, schema=ErrorSchema, description="Not allowed")
    def post(self, payload: dict[str, Any]) -> Event:
        return request_scope().create_event().execute(current_actor(), EventDetails(**payload))


@blueprint.route(f"/<int(max={MAX_DATABASE_ID}):event_id>")
class EventItem(MethodView):
    @optionally_authenticated
    @blueprint.doc(
        security=OPTIONAL_BEARER_SECURITY,
        description="Unpublished events are only visible to users allowed to manage them.",
    )
    @blueprint.response(HTTPStatus.OK, EventSchema)
    @blueprint.alt_response(HTTPStatus.UNAUTHORIZED, schema=ErrorSchema, description="Bad token")
    @blueprint.alt_response(HTTPStatus.NOT_FOUND, schema=ErrorSchema, description="Not found")
    def get(self, event_id: int) -> Event:
        return request_scope().get_event().execute(event_id, current_actor_or_none())

    @authenticated
    @blueprint.doc(
        security=BEARER_SECURITY,
        description="Replaces the editable fields. Organizers can only update their own events. "
        "Allowed status transitions: DRAFT→PUBLISHED, DRAFT→CANCELLED, PUBLISHED→CANCELLED, "
        "PUBLISHED→COMPLETED.",
    )
    @blueprint.arguments(EventUpdateSchema)
    @blueprint.response(HTTPStatus.OK, EventSchema)
    @blueprint.alt_response(HTTPStatus.UNAUTHORIZED, schema=ErrorSchema, description="Bad token")
    @blueprint.alt_response(HTTPStatus.FORBIDDEN, schema=ErrorSchema, description="Not allowed")
    @blueprint.alt_response(HTTPStatus.NOT_FOUND, schema=ErrorSchema, description="Not found")
    @blueprint.alt_response(
        HTTPStatus.CONFLICT, schema=ErrorSchema, description="Invalid state transition or edit"
    )
    def put(self, payload: dict[str, Any], event_id: int) -> Event:
        status = payload.pop("status")
        command = UpdateEventCommand(
            event_id=event_id, details=EventDetails(**payload), status=status
        )
        return request_scope().update_event().execute(current_actor(), command)

    @authenticated
    @blueprint.doc(
        security=BEARER_SECURITY,
        description="DRAFT events are deleted (204). PUBLISHED events are cancelled instead and "
        "returned (200). CANCELLED and COMPLETED events cannot be removed (409).",
    )
    @blueprint.response(HTTPStatus.OK, EventSchema, description="Published event was cancelled")
    @blueprint.alt_response(HTTPStatus.NO_CONTENT, description="Draft event was deleted")
    @blueprint.alt_response(HTTPStatus.UNAUTHORIZED, schema=ErrorSchema, description="Bad token")
    @blueprint.alt_response(HTTPStatus.FORBIDDEN, schema=ErrorSchema, description="Not allowed")
    @blueprint.alt_response(HTTPStatus.NOT_FOUND, schema=ErrorSchema, description="Not found")
    @blueprint.alt_response(
        HTTPStatus.CONFLICT, schema=ErrorSchema, description="Event cannot be removed"
    )
    def delete(self, event_id: int) -> Event | Response:
        result = request_scope().delete_event().execute(current_actor(), event_id)
        if result.event is None:
            return Response(status=HTTPStatus.NO_CONTENT)
        return result.event
