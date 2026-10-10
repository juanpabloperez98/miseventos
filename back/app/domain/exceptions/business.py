from app.domain.exceptions.base import (
    AuthenticationError,
    ConflictError,
    ExternalServiceError,
    ServiceUnavailableError,
)


class EmailAlreadyRegisteredError(ConflictError):
    default_message = "Email is already registered"


class AlreadyRegisteredToEventError(ConflictError):
    default_message = "User is already registered to this event"


class EventNotOpenForRegistrationError(ConflictError):
    default_message = "Event is not open for registration"


class EventCapacityExceededError(ConflictError):
    default_message = "Event has reached its capacity"


class InvalidEventStatusTransitionError(ConflictError):
    default_message = "Invalid event status transition"


class EventNotEditableError(ConflictError):
    default_message = "Cancelled or completed events cannot be modified"


class EventCannotBeRemovedError(ConflictError):
    default_message = "Only draft or published events can be removed"


class EventCapacityBelowRegistrationsError(ConflictError):
    default_message = "Capacity cannot be lower than the number of registered attendees"


class InvalidCredentialsError(AuthenticationError):
    default_message = "Invalid email or password"


class InvalidTokenError(AuthenticationError):
    default_message = "Invalid or expired token"


# Messages never include credentials nor details of the image service.
class ImageStorageError(ExternalServiceError):
    default_message = "The image service could not complete the operation"


class ImageStorageUnavailableError(ImageStorageError, ServiceUnavailableError):
    default_message = "Image uploads are not configured"
