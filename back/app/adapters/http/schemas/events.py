from marshmallow import Schema, fields, validate

from app.adapters.http.schemas.common import (
    MAX_CAPACITY,
    PageMetadataSchema,
    PaginationQuerySchema,
    UtcDateTime,
)
from app.adapters.http.schemas.event_images import EventImageSchema
from app.domain.enums import EventStatus


class EventQuerySchema(PaginationQuerySchema):
    search = fields.String(
        validate=validate.Length(max=100),
        metadata={"description": "Case-insensitive text matched against the event name"},
    )
    status = fields.Enum(
        EventStatus,
        metadata={
            "description": "Only events in this status. Unpublished events are only "
            "returned to users allowed to manage them"
        },
    )


class EventCreateSchema(Schema):
    name = fields.String(required=True, validate=validate.Length(max=200))
    description = fields.String(
        allow_none=True, load_default=None, validate=validate.Length(max=5000)
    )
    location = fields.String(required=True, validate=validate.Length(max=255))
    start_date = UtcDateTime(required=True)
    end_date = UtcDateTime(required=True)
    capacity = fields.Integer(required=True, strict=True, validate=validate.Range(max=MAX_CAPACITY))


class EventUpdateSchema(EventCreateSchema):
    status = fields.Enum(
        EventStatus,
        load_default=None,
        metadata={"description": "Target status. Omit to keep the current one"},
    )


class EventSchema(Schema):
    id = fields.Integer(required=True)
    name = fields.String(required=True)
    description = fields.String(allow_none=True)
    location = fields.String(required=True)
    start_date = UtcDateTime(required=True)
    end_date = UtcDateTime(required=True)
    capacity = fields.Integer(required=True)
    status = fields.Enum(EventStatus, required=True)
    created_by = fields.Integer(required=True)
    image = fields.Nested(
        EventImageSchema, allow_none=True, metadata={"description": "Cover image, if any"}
    )
    created_at = UtcDateTime()
    updated_at = UtcDateTime()


class EventPageSchema(PageMetadataSchema):
    items = fields.List(fields.Nested(EventSchema), required=True)
