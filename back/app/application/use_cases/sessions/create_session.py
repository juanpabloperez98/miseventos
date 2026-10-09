import logging

from app.application.dto import Actor, CreateSessionCommand, SessionView
from app.application.services import EventAccessPolicy
from app.application.use_cases.sessions._managed_session import (
    ensure_speaker_exists,
    load_event_for_session_management,
)
from app.application.use_cases.sessions._session_views import to_session_view
from app.domain.entities import Session
from app.domain.ports import EventRepository, SessionRepository, SpeakerRepository, UnitOfWork

logger = logging.getLogger(__name__)


class CreateSessionUseCase:
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

    def execute(self, actor: Actor, command: CreateSessionCommand) -> SessionView:
        event = load_event_for_session_management(
            self._events, self._access_policy, actor, command.event_id
        )
        details = command.details
        ensure_speaker_exists(self._speakers, details.speaker_id)

        session = Session(
            event_id=command.event_id,
            title=details.title,
            description=details.description,
            start_time=details.start_time,
            end_time=details.end_time,
            capacity=details.capacity,
            speaker_id=details.speaker_id,
        )
        session.ensure_fits_within(event)

        created = self._sessions.add(session)
        self._unit_of_work.commit()

        logger.info(
            "session_created",
            extra={"session_id": created.id, "event_id": event.id, "user_id": actor.user_id},
        )
        return to_session_view(created, self._speakers)
