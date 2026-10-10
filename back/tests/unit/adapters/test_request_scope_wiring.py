import ast
from pathlib import Path

import pytest

import app
from app.container import RequestScope

ROUTES_DIR = Path(app.__file__).parent / "adapters" / "http" / "routes"


def _requested_factories() -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for module in sorted(ROUTES_DIR.glob("*.py")):
        for node in ast.walk(ast.parse(module.read_text(encoding="utf-8"))):
            if (
                isinstance(node, ast.Attribute)
                and isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Name)
                and node.value.func.id == "request_scope"
            ):
                found.append((module.name, node.attr))
    return found


FACTORIES = _requested_factories()


def test_routes_request_use_cases_from_the_scope() -> None:
    modules_using_scope = {
        module.name
        for module in ROUTES_DIR.glob("*.py")
        if "request_scope()" in module.read_text(encoding="utf-8")
    }

    assert ("event_images.py", "authorize_event_image_upload") in FACTORIES
    assert {module for module, _ in FACTORIES} == modules_using_scope


@pytest.mark.parametrize(("module", "factory"), FACTORIES)
def test_request_scope_provides_every_factory_used_by_the_routes(module: str, factory: str) -> None:
    attribute = getattr(RequestScope, factory, None)

    assert attribute is not None, f"{module} calls request_scope().{factory}(), which is missing"
    assert callable(attribute) or isinstance(attribute, property)
