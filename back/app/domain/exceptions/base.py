class DomainError(Exception):
    default_message = "Domain error"

    def __init__(self, message: str | None = None) -> None:
        self.message = message or self.default_message
        super().__init__(self.message)


class InvalidValueError(DomainError):
    default_message = "Invalid value"


class NotFoundError(DomainError):
    default_message = "Resource not found"

    @classmethod
    def for_entity(cls, entity_name: str) -> "NotFoundError":
        return cls(f"{entity_name} not found")


class ConflictError(DomainError):
    default_message = "The request conflicts with the current state of the resource"


class AuthenticationError(DomainError):
    default_message = "Authentication required"


class AuthorizationError(DomainError):
    default_message = "You do not have permission to perform this action"


class ExternalServiceError(DomainError):
    default_message = "An external service failed"


class ServiceUnavailableError(ExternalServiceError):
    default_message = "The service is not available"
