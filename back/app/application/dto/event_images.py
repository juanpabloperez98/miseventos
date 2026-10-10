from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ImageUploadRequest:
    """What the client declares about the file it wants to upload (never the file itself)."""

    event_id: int
    filename: str
    content_type: str
    size: int


@dataclass(frozen=True, slots=True)
class ConfirmImageCommand:
    event_id: int
    public_id: str
