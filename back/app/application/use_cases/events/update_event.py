import logging

from app.application.dto import Actor, UpdateEventCommand
from app.application.services import EventAccessPolicy
from app.application.use_cases.events._managed_event import load_event_for_management
from app.domain.entities import Event
from app.domain.ports import EventRepository, RegistrationRepository, UnitOfWork

logger = logging.getLogger(__name__)


class UpdateEventUseCase:
    def __init__(
        self,
        events: EventRepository,
        registrations: RegistrationRepository,
        access_policy: EventAccessPolicy,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._events = events
        self._registrations = registrations
        self._access_policy = access_policy
        self._unit_of_work = unit_of_work

    def execute(self, actor: Actor, command: UpdateEventCommand) -> Event:
        event = load_event_for_management(
            self._events, self._access_policy, actor, command.event_id
        )
        details = command.details
        updated = event.with_details(
            name=details.name,
            description=details.description,
            location=details.location,
            start_date=details.start_date,
            end_date=details.end_date,
            capacity=details.capacity,
            registered_count=self._registrations.count_by_event(command.event_id),
        )
        if command.status is not None:
            updated = updated.with_status(command.status)

        saved = self._events.update(updated)
        self._unit_of_work.commit()

        logger.info(
            "event_updated",
            extra={"event_id": saved.id, "user_id": actor.user_id, "status": saved.status.value},
        )
        return saved
