from collections.abc import Mapping

from app.domain.enums import Permission, UserRole
from app.domain.exceptions import AuthorizationError

ROLE_PERMISSIONS: Mapping[UserRole, frozenset[Permission]] = {
    UserRole.ADMIN: frozenset(Permission),
    UserRole.ORGANIZER: frozenset(
        {
            Permission.MANAGE_EVENTS,
            Permission.MANAGE_SESSIONS,
            Permission.MANAGE_SPEAKERS,
            Permission.REGISTER_TO_EVENTS,
        }
    ),
    UserRole.ATTENDEE: frozenset({Permission.REGISTER_TO_EVENTS}),
}


class AuthorizationService:
    def __init__(
        self, role_permissions: Mapping[UserRole, frozenset[Permission]] = ROLE_PERMISSIONS
    ) -> None:
        self._role_permissions = role_permissions

    def is_allowed(self, role: UserRole, permission: Permission) -> bool:
        return permission in self._role_permissions.get(role, frozenset())

    def ensure_allowed(self, role: UserRole, permission: Permission) -> None:
        if not self.is_allowed(role, permission):
            raise AuthorizationError()
