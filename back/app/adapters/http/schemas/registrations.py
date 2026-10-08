from marshmallow import Schema, fields


class RegistrationRequestSchema(Schema):
    pass


class RegistrationSchema(Schema):
    id = fields.Integer(required=True)
    event_id = fields.Integer(required=True)
    user_id = fields.Integer(required=True)
    registered_at = fields.AwareDateTime(required=True)
