from collections.abc import Callable
from functools import wraps

from flask import g, request

from app.adapters.http.dependencies import request_scope
from app.application.dto import UserDTO
from app.domain.exceptions import AuthenticationError

_BEARER_PREFIX = "bearer "


def authenticated[**P, R](view: Callable[P, R]) -> Callable[P, R]:
    @wraps(view)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        token = _extract_bearer_token(request.headers.get("Authorization"))
        g.current_user = request_scope().authenticate_user().execute(token)
        return view(*args, **kwargs)

    return wrapper


def current_user() -> UserDTO:
    user: UserDTO | None = g.get("current_user")
    if user is None:
        raise AuthenticationError()
    return user


def _extract_bearer_token(header: str | None) -> str:
    if not header:
        raise AuthenticationError("Missing bearer token")
    if not header.lower().startswith(_BEARER_PREFIX):
        raise AuthenticationError("Authorization header must use the Bearer scheme")
    token = header[len(_BEARER_PREFIX) :].strip()
    if not token:
        raise AuthenticationError("Missing bearer token")
    return token
