from datetime import UTC, datetime
from typing import Any

from marshmallow import Schema, fields, validate

from app.domain.value_objects import MAX_PER_PAGE

MAX_PAGE = 100_000
MAX_DATABASE_ID = 2_147_483_647
MAX_CAPACITY = 1_000_000


class UtcDateTime(fields.AwareDateTime):
    """Instant exchanged as ISO 8601 in UTC.

    Input must include an offset (naive values are rejected) and is normalized to UTC. Output is
    converted to UTC too, so the API does not depend on the timezone of the database session
    (PostgreSQL returns ``timestamptz`` values in the session ``TimeZone``).
    """

    def _serialize(self, value: datetime | None, attr: str | None, obj: Any, **kwargs: Any) -> Any:
        if value is not None and value.tzinfo is not None:
            value = value.astimezone(UTC)
        return super()._serialize(value, attr, obj, **kwargs)

    def _deserialize(self, value: Any, attr: str | None, data: Any, **kwargs: Any) -> datetime:
        return super()._deserialize(value, attr, data, **kwargs).astimezone(UTC)


class ErrorSchema(Schema):
    message = fields.String(required=True, metadata={"example": "Event not found"})
    errors = fields.Dict(metadata={"description": "Field level validation errors"})


class PaginationQuerySchema(Schema):
    page = fields.Integer(load_default=1, validate=validate.Range(min=1, max=MAX_PAGE))
    per_page = fields.Integer(load_default=10, validate=validate.Range(min=1, max=MAX_PER_PAGE))


class PageMetadataSchema(Schema):
    total = fields.Integer(required=True)
    page = fields.Integer(required=True)
    per_page = fields.Integer(required=True)
    pages = fields.Integer(required=True)
