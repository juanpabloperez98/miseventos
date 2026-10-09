from marshmallow import Schema, fields

from app.adapters.http.schemas.common import PageMetadataSchema


class SpeakerSchema(Schema):
    """Public speaker data. The email is personal data and is never exposed."""

    id = fields.Integer(required=True)
    name = fields.String(required=True)
    bio = fields.String(allow_none=True)


class SpeakerPageSchema(PageMetadataSchema):
    items = fields.List(fields.Nested(SpeakerSchema), required=True)
