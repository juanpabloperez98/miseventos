import logging

from app.application.dto import Actor
from app.application.services import AuthorizationService, EventAccessPolicy
from app.domain.entities import Registration
from app.domain.enums import Permission
from app.domain.exceptions import AlreadyRegisteredToEventError, NotFoundError
from app.domain.ports import EventRepository, RegistrationRepository, UnitOfWork

logger = logging.getLogger(__name__)


class RegisterForEventUseCase:
    def __init__(
        self,
        events: EventRepository,
        registrations: RegistrationRepository,
        authorization: AuthorizationService,
        access_policy: EventAccessPolicy,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._events = events
        self._registrations = registrations
        self._authorization = authorization
        self._access_policy = access_policy
        self._unit_of_work = unit_of_work

    def execute(self, actor: Actor, event_id: int) -> Registration:
        self._authorization.ensure_allowed(actor.role, Permission.REGISTER_TO_EVENTS)

        event = self._events.get_by_id_for_update(event_id)
        if event is None or not self._access_policy.can_view(actor, event):
            raise NotFoundError.for_entity("Event")
        if self._registrations.get(actor.user_id, event_id) is not None:
            raise AlreadyRegisteredToEventError()
        event.ensure_can_accept_registration(self._registrations.count_by_event(event_id))

        registration = self._registrations.add(
            Registration(user_id=actor.user_id, event_id=event_id)
        )
        self._unit_of_work.commit()

        logger.info(
            "event_registration_created",
            extra={"event_id": event_id, "user_id": actor.user_id},
        )
        return registration
