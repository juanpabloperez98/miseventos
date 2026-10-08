from app.domain.exceptions.base import (
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    DomainError,
    InvalidValueError,
    NotFoundError,
)
from app.domain.exceptions.business import (
    AlreadyRegisteredToEventError,
    EmailAlreadyRegisteredError,
    EventCannotBeRemovedError,
    EventCapacityBelowRegistrationsError,
    EventCapacityExceededError,
    EventNotEditableError,
    EventNotOpenForRegistrationError,
    InvalidCredentialsError,
    InvalidEventStatusTransitionError,
    InvalidTokenError,
)

__all__ = [
    "AlreadyRegisteredToEventError",
    "AuthenticationError",
    "AuthorizationError",
    "ConflictError",
    "DomainError",
    "EmailAlreadyRegisteredError",
    "EventCannotBeRemovedError",
    "EventCapacityBelowRegistrationsError",
    "EventCapacityExceededError",
    "EventNotEditableError",
    "EventNotOpenForRegistrationError",
    "InvalidCredentialsError",
    "InvalidEventStatusTransitionError",
    "InvalidTokenError",
    "InvalidValueError",
    "NotFoundError",
]
