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
from app.adapters.http.schemas.common import MAX_DATABASE_ID, ErrorSchema
from app.adapters.http.schemas.sessions import SessionSchema, SessionWriteSchema
from app.application.dto import CreateSessionCommand, SessionDetails, UpdateSessionCommand
from app.domain.entities import Session

blueprint = Blueprint("sessions", __name__, url_prefix="/api", description="Event sessions")

ID = f"int(max={MAX_DATABASE_ID})"


@blueprint.route(f"/events/<{ID}:event_id>/sessions")
class EventSessionCollection(MethodView):
    @optionally_authenticated
    @blueprint.doc(
        security=OPTIONAL_BEARER_SECURITY,
        description="Sessions of an event, ordered by start time. Only available when the "
        "event is visible to the caller.",
    )
    @blueprint.response(HTTPStatus.OK, SessionSchema(many=True))
    @blueprint.alt_response(HTTPStatus.UNAUTHORIZED, schema=ErrorSchema, description="Bad token")
    @blueprint.alt_response(HTTPStatus.NOT_FOUND, schema=ErrorSchema, description="Not found")
    def get(self, event_id: int) -> list[Session]:
        return request_scope().list_event_sessions().execute(event_id, current_actor_or_none())

    @authenticated
    @blueprint.doc(
        security=BEARER_SECURITY,
        description="Organizers can only add sessions to their own events. The session must "
        "take place within the event schedule and the event must not be cancelled or completed.",
    )
    @blueprint.arguments(SessionWriteSchema)
    @blueprint.response(HTTPStatus.CREATED, SessionSchema)
    @blueprint.alt_response(HTTPStatus.UNAUTHORIZED, schema=ErrorSchema, description="Bad token")
    @blueprint.alt_response(HTTPStatus.FORBIDDEN, schema=ErrorSchema, description="Not allowed")
    @blueprint.alt_response(
        HTTPStatus.NOT_FOUND, schema=ErrorSchema, description="Event or speaker not found"
    )
    @blueprint.alt_response(
        HTTPStatus.CONFLICT, schema=ErrorSchema, description="Event cannot be modified"
    )
    def post(self, payload: dict[str, Any], event_id: int) -> Session:
        command = CreateSessionCommand(event_id=event_id, details=SessionDetails(**payload))
        return request_scope().create_session().execute(current_actor(), command)


@blueprint.route(f"/sessions/<{ID}:session_id>")
class SessionItem(MethodView):
    @optionally_authenticated
    @blueprint.doc(
        security=OPTIONAL_BEARER_SECURITY,
        description="Sessions of unpublished events are only visible to users allowed to "
        "manage the event.",
    )
    @blueprint.response(HTTPStatus.OK, SessionSchema)
    @blueprint.alt_response(HTTPStatus.UNAUTHORIZED, schema=ErrorSchema, description="Bad token")
    @blueprint.alt_response(HTTPStatus.NOT_FOUND, schema=ErrorSchema, description="Not found")
    def get(self, session_id: int) -> Session:
        return request_scope().get_session().execute(session_id, current_actor_or_none())

    @authenticated
    @blueprint.doc(
        security=BEARER_SECURITY,
        description="Replaces the editable fields. The session stays in its event.",
    )
    @blueprint.arguments(SessionWriteSchema)
    @blueprint.response(HTTPStatus.OK, SessionSchema)
    @blueprint.alt_response(HTTPStatus.UNAUTHORIZED, schema=ErrorSchema, description="Bad token")
    @blueprint.alt_response(HTTPStatus.FORBIDDEN, schema=ErrorSchema, description="Not allowed")
    @blueprint.alt_response(
        HTTPStatus.NOT_FOUND, schema=ErrorSchema, description="Session or speaker not found"
    )
    @blueprint.alt_response(
        HTTPStatus.CONFLICT, schema=ErrorSchema, description="Event cannot be modified"
    )
    def put(self, payload: dict[str, Any], session_id: int) -> Session:
        command = UpdateSessionCommand(session_id=session_id, details=SessionDetails(**payload))
        return request_scope().update_session().execute(current_actor(), command)

    @authenticated
    @blueprint.doc(security=BEARER_SECURITY)
    @blueprint.response(HTTPStatus.NO_CONTENT, description="Session deleted")
    @blueprint.alt_response(HTTPStatus.UNAUTHORIZED, schema=ErrorSchema, description="Bad token")
    @blueprint.alt_response(HTTPStatus.FORBIDDEN, schema=ErrorSchema, description="Not allowed")
    @blueprint.alt_response(HTTPStatus.NOT_FOUND, schema=ErrorSchema, description="Not found")
    @blueprint.alt_response(
        HTTPStatus.CONFLICT, schema=ErrorSchema, description="Event cannot be modified"
    )
    def delete(self, session_id: int) -> Response:
        request_scope().delete_session().execute(current_actor(), session_id)
        return Response(status=HTTPStatus.NO_CONTENT)
