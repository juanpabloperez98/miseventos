from marshmallow import Schema, fields, validate


class ImageUploadRequestSchema(Schema):
    filename = fields.String(required=True, validate=validate.Length(min=1, max=255))
    content_type = fields.String(
        required=True,
        validate=validate.Length(max=100),
        metadata={"description": "MIME type: image/jpeg, image/png or image/webp"},
    )
    size = fields.Integer(
        required=True,
        strict=True,
        validate=validate.Range(min=1),
        metadata={"description": "Bytes"},
    )


class SignedImageUploadSchema(Schema):
    """Fields to send with the file to `upload_url` (multipart). Never includes the API secret."""

    upload_url = fields.String(required=True)
    cloud_name = fields.String(required=True)
    api_key = fields.String(required=True)
    timestamp = fields.Integer(required=True)
    signature = fields.String(required=True)
    public_id = fields.String(required=True)
    allowed_formats = fields.String(required=True)


class ConfirmImageSchema(Schema):
    public_id = fields.String(
        required=True,
        validate=validate.Length(min=1, max=255),
        metadata={"description": "public_id returned by the upload authorization"},
    )


class EventImageSchema(Schema):
    public_id = fields.String(required=True)
    secure_url = fields.String(required=True)
    width = fields.Integer(required=True)
    height = fields.Integer(required=True)
    format = fields.String(required=True)
