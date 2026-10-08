from app.domain.exceptions.base import AuthenticationError, ConflictError


class EmailAlreadyRegisteredError(ConflictError):
    default_message = "Email is already registered"


class AlreadyRegisteredToEventError(ConflictError):
    default_message = "User is already registered to this event"


class EventNotOpenForRegistrationError(ConflictError):
    default_message = "Event is not open for registration"


class EventCapacityExceededError(ConflictError):
    default_message = "Event has reached its capacity"


class InvalidCredentialsError(AuthenticationError):
    default_message = "Invalid email or password"


class InvalidTokenError(AuthenticationError):
    default_message = "Invalid or expired token"
