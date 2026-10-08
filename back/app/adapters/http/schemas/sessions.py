from marshmallow import Schema, fields, validate

from app.adapters.http.schemas.common import MAX_CAPACITY, MAX_DATABASE_ID, UtcDateTime


class SessionWriteSchema(Schema):
    title = fields.String(required=True, validate=validate.Length(max=200))
    description = fields.String(
        allow_none=True, load_default=None, validate=validate.Length(max=5000)
    )
    start_time = UtcDateTime(required=True)
    end_time = UtcDateTime(required=True)
    capacity = fields.Integer(required=True, strict=True, validate=validate.Range(max=MAX_CAPACITY))
    speaker_id = fields.Integer(
        allow_none=True,
        load_default=None,
        strict=True,
        validate=validate.Range(min=1, max=MAX_DATABASE_ID),
        metadata={"description": "Optional speaker. Omit or send null for no speaker"},
    )


class SessionSchema(Schema):
    id = fields.Integer(required=True)
    event_id = fields.Integer(required=True)
    speaker_id = fields.Integer(allow_none=True)
    title = fields.String(required=True)
    description = fields.String(allow_none=True)
    start_time = fields.AwareDateTime(required=True)
    end_time = fields.AwareDateTime(required=True)
    capacity = fields.Integer(required=True)
    created_at = fields.AwareDateTime()
    updated_at = fields.AwareDateTime()
