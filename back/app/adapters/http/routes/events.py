from http import HTTPStatus
from typing import Any

from flask_smorest import Blueprint

from app.adapters.http.dependencies import request_scope
from app.adapters.http.schemas.events import EventPageSchema, EventQuerySchema
from app.application.dto import ListEventsQuery
from app.domain.entities import Event
from app.domain.value_objects import Page

blueprint = Blueprint("events", __name__, url_prefix="/api/events", description="Events")


@blueprint.route("")
@blueprint.arguments(EventQuerySchema, location="query")
@blueprint.response(HTTPStatus.OK, EventPageSchema)
def list_events(query: dict[str, Any]) -> Page[Event]:
    return request_scope().list_published_events().execute(ListEventsQuery(**query))
