from flask import current_app, g

from app.container import Container, RequestScope

CONTAINER_EXTENSION_KEY = "container"


def get_container() -> Container:
    container: Container = current_app.extensions[CONTAINER_EXTENSION_KEY]
    return container


def request_scope() -> RequestScope:
    if "request_scope" not in g:
        g.request_scope = get_container().create_request_scope()
    scope: RequestScope = g.request_scope
    return scope


def close_request_scope(_error: BaseException | None = None) -> None:
    scope: RequestScope | None = g.pop("request_scope", None)
    if scope is not None:
        scope.close()
