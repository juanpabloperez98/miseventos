from marshmallow import Schema, fields

from app.adapters.http.schemas.common import UtcDateTime


class RegistrationRequestSchema(Schema):
    pass


class RegistrationSchema(Schema):
    id = fields.Integer(required=True)
    event_id = fields.Integer(required=True)
    user_id = fields.Integer(required=True)
    registered_at = UtcDateTime(required=True)
