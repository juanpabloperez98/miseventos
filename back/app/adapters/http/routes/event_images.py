from http import HTTPStatus
from typing import Any

from flask import Response
from flask.views import MethodView
from flask_smorest import Blueprint

from app.adapters.http.dependencies import request_scope
from app.adapters.http.middleware import authenticated, current_actor
from app.adapters.http.openapi import BEARER_SECURITY
from app.adapters.http.schemas.common import MAX_DATABASE_ID, ErrorSchema
from app.adapters.http.schemas.event_images import (
    ConfirmImageSchema,
    EventImageSchema,
    ImageUploadRequestSchema,
    SignedImageUploadSchema,
)
from app.application.dto import ConfirmImageCommand, ImageUploadRequest
from app.domain.entities import EventImage
from app.domain.ports import SignedImageUpload

blueprint = Blueprint(
    "event_images", __name__, url_prefix="/api/events", description="Event cover images"
)

IMAGES_PATH = f"/<int(max={MAX_DATABASE_ID}):event_id>/images"


def _common_errors(view: Any) -> Any:
    for status, description in (
        (HTTPStatus.UNAUTHORIZED, "Bad token"),
        (HTTPStatus.FORBIDDEN, "Not allowed"),
        (HTTPStatus.NOT_FOUND, "Not found"),
        (HTTPStatus.CONFLICT, "Cancelled or completed event"),
        (HTTPStatus.BAD_GATEWAY, "Image service error"),
        (HTTPStatus.SERVICE_UNAVAILABLE, "Image uploads not configured"),
    ):
        view = blueprint.alt_response(status, schema=ErrorSchema, description=description)(view)
    return view


@blueprint.route(f"{IMAGES_PATH}/upload")
class EventImageUpload(MethodView):
    @authenticated
    @blueprint.doc(
        security=BEARER_SECURITY,
        description="Signs a direct upload of the cover image to Cloudinary. Send only the file "
        "metadata; then POST the file with the returned fields to `upload_url`. Allowed types: "
        "JPEG, PNG and WebP.",
    )
    @blueprint.arguments(ImageUploadRequestSchema)
    @blueprint.response(HTTPStatus.OK, SignedImageUploadSchema)
    @_common_errors
    def post(self, payload: dict[str, Any], event_id: int) -> SignedImageUpload:
        request = ImageUploadRequest(event_id=event_id, **payload)
        return request_scope().authorize_event_image_upload().execute(current_actor(), request)


@blueprint.route(f"{IMAGES_PATH}/confirm")
class EventImageConfirmation(MethodView):
    @authenticated
    @blueprint.doc(
        security=BEARER_SECURITY,
        description="Sets the uploaded image as the event cover after checking it with "
        "Cloudinary. The previous cover is deleted once the new one is saved.",
    )
    @blueprint.arguments(ConfirmImageSchema)
    @blueprint.response(HTTPStatus.CREATED, EventImageSchema)
    @_common_errors
    def post(self, payload: dict[str, Any], event_id: int) -> EventImage:
        command = ConfirmImageCommand(event_id=event_id, public_id=payload["public_id"])
        return request_scope().confirm_event_image().execute(current_actor(), command)


@blueprint.route(IMAGES_PATH)
class EventImageItem(MethodView):
    @authenticated
    @blueprint.doc(security=BEARER_SECURITY, description="Removes the cover image of the event.")
    @blueprint.response(HTTPStatus.NO_CONTENT)
    @_common_errors
    def delete(self, event_id: int) -> Response:
        request_scope().delete_event_image().execute(current_actor(), event_id)
        return Response(status=HTTPStatus.NO_CONTENT)
