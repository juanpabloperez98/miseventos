import logging
from collections.abc import Mapping
from http import HTTPStatus

from flask import Flask
from flask.typing import ResponseReturnValue

from app.domain.exceptions import (
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    DomainError,
    ExternalServiceError,
    InvalidValueError,
    NotFoundError,
    ServiceUnavailableError,
)

logger = logging.getLogger(__name__)

STATUS_BY_ERROR: Mapping[type[DomainError], HTTPStatus] = {
    InvalidValueError: HTTPStatus.UNPROCESSABLE_ENTITY,
    NotFoundError: HTTPStatus.NOT_FOUND,
    ConflictError: HTTPStatus.CONFLICT,
    AuthenticationError: HTTPStatus.UNAUTHORIZED,
    AuthorizationError: HTTPStatus.FORBIDDEN,
    ServiceUnavailableError: HTTPStatus.SERVICE_UNAVAILABLE,
    ExternalServiceError: HTTPStatus.BAD_GATEWAY,
}


def status_for(error: DomainError) -> HTTPStatus:
    for error_type in type(error).__mro__:
        if error_type in STATUS_BY_ERROR:
            return STATUS_BY_ERROR[error_type]
    return HTTPStatus.BAD_REQUEST


def handle_domain_error(error: DomainError) -> ResponseReturnValue:
    status = status_for(error)
    logger.info("domain_error", extra={"error": type(error).__name__, "status": status.value})
    headers = {"WWW-Authenticate": "Bearer"} if status is HTTPStatus.UNAUTHORIZED else {}
    return {"message": error.message}, status, headers


def handle_unexpected_error(error: Exception) -> ResponseReturnValue:
    logger.exception("unhandled_error", exc_info=error)
    return {"message": "Internal server error"}, HTTPStatus.INTERNAL_SERVER_ERROR


def register_error_handlers(app: Flask) -> None:
    app.register_error_handler(DomainError, handle_domain_error)
    app.register_error_handler(Exception, handle_unexpected_error)
