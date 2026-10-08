from marshmallow import Schema, fields, validate

from app.domain.value_objects import MAX_PER_PAGE


class ErrorSchema(Schema):
    message = fields.String(required=True, metadata={"example": "Event not found"})
    errors = fields.Dict(metadata={"description": "Field level validation errors"})


class PaginationQuerySchema(Schema):
    page = fields.Integer(load_default=1, validate=validate.Range(min=1))
    per_page = fields.Integer(load_default=10, validate=validate.Range(min=1, max=MAX_PER_PAGE))


class PageMetadataSchema(Schema):
    total = fields.Integer(required=True)
    page = fields.Integer(required=True)
    per_page = fields.Integer(required=True)
    pages = fields.Integer(required=True)
