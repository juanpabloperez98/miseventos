from app.domain.exceptions import InvalidValueError


def require_text(value: str, field_name: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise InvalidValueError(f"{field_name} must not be blank")
    return stripped


def optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    return value.strip() or None


def require_positive(value: int, field_name: str) -> int:
    if value <= 0:
        raise InvalidValueError(f"{field_name} must be greater than zero")
    return value
