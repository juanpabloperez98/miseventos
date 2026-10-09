from marshmallow import Schema, fields, validate

from app.adapters.http.schemas.common import UtcDateTime
from app.domain.enums import UserRole

PASSWORD_LENGTH = validate.Length(min=8, max=128)


class RegisterRequestSchema(Schema):
    name = fields.String(required=True, validate=validate.Length(min=1, max=120))
    email = fields.Email(required=True, validate=validate.Length(max=255))
    password = fields.String(required=True, load_only=True, validate=PASSWORD_LENGTH)


class LoginRequestSchema(Schema):
    email = fields.String(required=True, validate=validate.Length(min=1, max=255))
    password = fields.String(required=True, load_only=True, validate=validate.Length(min=1))


class AccessTokenSchema(Schema):
    access_token = fields.String(required=True, attribute="value")
    token_type = fields.String(required=True, metadata={"example": "Bearer"})
    expires_at = UtcDateTime(required=True)


class UserSchema(Schema):
    id = fields.Integer(required=True)
    name = fields.String(required=True)
    email = fields.Email(required=True)
    role = fields.Enum(UserRole, required=True)
    created_at = UtcDateTime()
    updated_at = UtcDateTime()
