from collections.abc import Callable
from functools import wraps

from flask import g, request

from app.adapters.http.dependencies import request_scope
from app.application.dto import Actor, UserDTO
from app.domain.exceptions import AuthenticationError

_BEARER_PREFIX = "bearer "


def authenticated[**P, R](view: Callable[P, R]) -> Callable[P, R]:
    @wraps(view)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        g.current_user = _authenticate(request.headers.get("Authorization"))
        return view(*args, **kwargs)

    return wrapper


def optionally_authenticated[**P, R](view: Callable[P, R]) -> Callable[P, R]:
    """Anonymous requests are allowed, but a supplied token must be valid."""

    @wraps(view)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        header = request.headers.get("Authorization")
        g.current_user = _authenticate(header) if header is not None else None
        return view(*args, **kwargs)

    return wrapper


def current_user() -> UserDTO:
    user: UserDTO | None = g.get("current_user")
    if user is None:
        raise AuthenticationError()
    return user


def current_actor() -> Actor:
    return Actor.from_user(current_user())


def current_actor_or_none() -> Actor | None:
    user: UserDTO | None = g.get("current_user")
    return Actor.from_user(user) if user is not None else None


def _authenticate(header: str | None) -> UserDTO:
    return request_scope().authenticate_user().execute(_extract_bearer_token(header))


def _extract_bearer_token(header: str | None) -> str:
    if not header:
        raise AuthenticationError("Missing bearer token")
    if not header.lower().startswith(_BEARER_PREFIX):
        raise AuthenticationError("Authorization header must use the Bearer scheme")
    token = header[len(_BEARER_PREFIX) :].strip()
    if not token:
        raise AuthenticationError("Missing bearer token")
    return token
