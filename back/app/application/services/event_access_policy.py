from app.application.dto import Actor
from app.application.services.authorization_service import AuthorizationService
from app.domain.entities import Event
from app.domain.enums import Permission
from app.domain.exceptions import AuthorizationError
from app.domain.ports import EventVisibility


class EventAccessPolicy:
    def __init__(self, authorization: AuthorizationService) -> None:
        self._authorization = authorization

    def ensure_can_manage_events(self, actor: Actor) -> None:
        self._authorization.ensure_allowed(actor.role, Permission.MANAGE_EVENTS)

    def ensure_can_manage_sessions(self, actor: Actor) -> None:
        self._authorization.ensure_allowed(actor.role, Permission.MANAGE_SESSIONS)

    def can_manage(self, actor: Actor, event: Event) -> bool:
        if self._authorization.is_allowed(actor.role, Permission.MANAGE_ANY_EVENT):
            return True
        return self._authorization.is_allowed(
            actor.role, Permission.MANAGE_EVENTS
        ) and event.is_owned_by(actor.user_id)

    def ensure_can_manage(self, actor: Actor, event: Event) -> None:
        if not self.can_manage(actor, event):
            raise AuthorizationError("You can only manage your own events")

    def can_view(self, actor: Actor | None, event: Event) -> bool:
        return event.is_publicly_visible or (actor is not None and self.can_manage(actor, event))

    def visibility_for(self, actor: Actor | None) -> EventVisibility:
        if actor is None:
            return EventVisibility.public()
        if self._authorization.is_allowed(actor.role, Permission.MANAGE_ANY_EVENT):
            return EventVisibility.unrestricted()
        if self._authorization.is_allowed(actor.role, Permission.MANAGE_EVENTS):
            return EventVisibility.public_or_owned_by(actor.user_id)
        return EventVisibility.public()
