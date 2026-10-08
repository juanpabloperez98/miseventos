import ast
import importlib
import inspect
import pkgutil
from pathlib import Path

import pytest

import app
from app.domain import ports
from app.infrastructure.database import repositories, unit_of_work
from app.infrastructure.security import JwtTokenService, Sha256PasswordHasher

APP_ROOT = Path(app.__file__).parent

FRAMEWORKS = (
    "flask",
    "flask_smorest",
    "flask_cors",
    "werkzeug",
    "marshmallow",
    "sqlalchemy",
    "alembic",
    "psycopg",
    "jwt",
    "dotenv",
)
OUTER_LAYERS = ("app.infrastructure", "app.adapters", "app.container", "app.bootstrap")

FORBIDDEN_IMPORTS = {
    "domain": (*FRAMEWORKS, "app.application", *OUTER_LAYERS),
    "application": (*FRAMEWORKS, *OUTER_LAYERS),
    "infrastructure": ("flask", "flask_smorest", "flask_cors", "marshmallow", "app.adapters"),
}


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def _is_forbidden(module: str, forbidden: tuple[str, ...]) -> bool:
    return any(module == prefix or module.startswith(f"{prefix}.") for prefix in forbidden)


@pytest.mark.parametrize("layer", sorted(FORBIDDEN_IMPORTS))
def test_layer_does_not_depend_on_forbidden_modules(layer: str) -> None:
    violations = [
        f"{path.relative_to(APP_ROOT)} imports {module}"
        for path in (APP_ROOT / layer).rglob("*.py")
        for module in _imported_modules(path)
        if _is_forbidden(module, FORBIDDEN_IMPORTS[layer])
    ]

    assert violations == []


def test_every_module_imports_without_circular_dependencies() -> None:
    for module in pkgutil.walk_packages(app.__path__, prefix="app."):
        importlib.import_module(module.name)


def test_concrete_adapters_implement_domain_ports() -> None:
    implementations = {
        repositories.SqlAlchemyUserRepository: ports.UserRepository,
        repositories.SqlAlchemyEventRepository: ports.EventRepository,
        repositories.SqlAlchemyRegistrationRepository: ports.RegistrationRepository,
        repositories.SqlAlchemySpeakerRepository: ports.SpeakerRepository,
        repositories.SqlAlchemySessionRepository: ports.SessionRepository,
        unit_of_work.SqlAlchemyUnitOfWork: ports.UnitOfWork,
        Sha256PasswordHasher: ports.PasswordHasher,
        JwtTokenService: ports.TokenService,
    }

    for implementation, port in implementations.items():
        assert issubclass(implementation, port)
        assert not inspect.isabstract(implementation), implementation.__name__
