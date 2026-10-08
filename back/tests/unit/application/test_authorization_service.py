import pytest

from app.application.services import AuthorizationService
from app.domain.enums import Permission, UserRole
from app.domain.exceptions import AuthorizationError


@pytest.mark.parametrize("permission", list(Permission))
def test_admin_has_every_permission(permission: Permission) -> None:
    assert AuthorizationService().is_allowed(UserRole.ADMIN, permission)


@pytest.mark.parametrize(
    "permission", [Permission.MANAGE_EVENTS, Permission.MANAGE_SESSIONS, Permission.MANAGE_SPEAKERS]
)
def test_attendee_cannot_manage_resources(permission: Permission) -> None:
    with pytest.raises(AuthorizationError):
        AuthorizationService().ensure_allowed(UserRole.ATTENDEE, permission)


def test_attendee_can_register_to_events() -> None:
    AuthorizationService().ensure_allowed(UserRole.ATTENDEE, Permission.REGISTER_TO_EVENTS)


def test_organizer_can_manage_events() -> None:
    assert AuthorizationService().is_allowed(UserRole.ORGANIZER, Permission.MANAGE_EVENTS)


def test_role_permissions_can_be_replaced_without_modifying_the_service() -> None:
    service = AuthorizationService({UserRole.ATTENDEE: frozenset({Permission.MANAGE_SPEAKERS})})

    assert service.is_allowed(UserRole.ATTENDEE, Permission.MANAGE_SPEAKERS)
    assert not service.is_allowed(UserRole.ADMIN, Permission.MANAGE_EVENTS)
