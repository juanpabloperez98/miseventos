from collections.abc import Callable
from functools import wraps

from app.adapters.http.dependencies import request_scope
from app.adapters.http.middleware.authentication import current_user
from app.domain.enums import Permission


def require_permission[**P, R](
    permission: Permission,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Must be applied below ``@authenticated`` so the current user is already resolved."""

    def decorator(view: Callable[P, R]) -> Callable[P, R]:
        @wraps(view)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            request_scope().authorization.ensure_allowed(current_user().role, permission)
            return view(*args, **kwargs)

        return wrapper

    return decorator
