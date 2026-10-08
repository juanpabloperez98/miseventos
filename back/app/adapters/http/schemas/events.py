from marshmallow import Schema, fields, validate

from app.adapters.http.schemas.common import PageMetadataSchema, PaginationQuerySchema
from app.domain.enums import EventStatus


class EventQuerySchema(PaginationQuerySchema):
    search = fields.String(
        validate=validate.Length(max=100),
        metadata={
            "description": "Case-insensitive text matched against name, description and location"
        },
    )


class EventSchema(Schema):
    id = fields.Integer(required=True)
    name = fields.String(required=True)
    description = fields.String(allow_none=True)
    location = fields.String(required=True)
    start_date = fields.AwareDateTime(required=True)
    end_date = fields.AwareDateTime(required=True)
    capacity = fields.Integer(required=True)
    status = fields.Enum(EventStatus, required=True)
    created_by = fields.Integer(required=True)
    created_at = fields.AwareDateTime()
    updated_at = fields.AwareDateTime()


class EventPageSchema(PageMetadataSchema):
    items = fields.List(fields.Nested(EventSchema), required=True)
