from http import HTTPStatus
from typing import Any

from flask_smorest import Blueprint

from app.adapters.http.dependencies import request_scope
from app.adapters.http.middleware import optionally_authenticated
from app.adapters.http.openapi import OPTIONAL_BEARER_SECURITY
from app.adapters.http.schemas.common import ErrorSchema, PaginationQuerySchema
from app.adapters.http.schemas.speakers import SpeakerPageSchema
from app.domain.entities import Speaker
from app.domain.value_objects import Page

blueprint = Blueprint("speakers", __name__, url_prefix="/api/speakers", description="Speakers")


@blueprint.route("")
@optionally_authenticated
@blueprint.doc(
    security=OPTIONAL_BEARER_SECURITY,
    description="Paginated speaker catalog ordered by name (read-only). Used to show and assign "
    "the speakers of sessions. Emails are not exposed.",
)
@blueprint.arguments(PaginationQuerySchema, location="query")
@blueprint.response(HTTPStatus.OK, SpeakerPageSchema)
@blueprint.alt_response(HTTPStatus.UNAUTHORIZED, schema=ErrorSchema, description="Bad token")
def list_speakers(query: dict[str, Any]) -> Page[Speaker]:
    return request_scope().list_speakers().execute(**query)
