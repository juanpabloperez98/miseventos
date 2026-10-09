import logging

from app.application.dto import Actor, SessionView, UpdateSessionCommand
from app.application.services import EventAccessPolicy
from app.application.use_cases.sessions._managed_session import (
    ensure_speaker_exists,
    load_session_for_management,
)
from app.application.use_cases.sessions._session_views import to_session_view
from app.domain.ports import EventRepository, SessionRepository, SpeakerRepository, UnitOfWork

logger = logging.getLogger(__name__)


class UpdateSessionUseCase:
    def __init__(
        self,
        sessions: SessionRepository,
        events: EventRepository,
        speakers: SpeakerRepository,
        access_policy: EventAccessPolicy,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._sessions = sessions
        self._events = events
        self._speakers = speakers
        self._access_policy = access_policy
        self._unit_of_work = unit_of_work

    def execute(self, actor: Actor, command: UpdateSessionCommand) -> SessionView:
        session, event = load_session_for_management(
            self._sessions, self._events, self._access_policy, actor, command.session_id
        )
        details = command.details
        ensure_speaker_exists(self._speakers, details.speaker_id)

        updated = session.with_details(
            title=details.title,
            description=details.description,
            start_time=details.start_time,
            end_time=details.end_time,
            capacity=details.capacity,
            speaker_id=details.speaker_id,
        )
        updated.ensure_fits_within(event)

        saved = self._sessions.update(updated)
        self._unit_of_work.commit()

        logger.info(
            "session_updated",
            extra={"session_id": saved.id, "event_id": event.id, "user_id": actor.user_id},
        )
        return to_session_view(saved, self._speakers)
