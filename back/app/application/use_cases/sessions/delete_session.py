import logging

from app.application.dto import Actor
from app.application.services import EventAccessPolicy
from app.application.use_cases.sessions._managed_session import load_session_for_management
from app.domain.ports import EventRepository, SessionRepository, UnitOfWork

logger = logging.getLogger(__name__)


class DeleteSessionUseCase:
    def __init__(
        self,
        sessions: SessionRepository,
        events: EventRepository,
        access_policy: EventAccessPolicy,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._sessions = sessions
        self._events = events
        self._access_policy = access_policy
        self._unit_of_work = unit_of_work

    def execute(self, actor: Actor, session_id: int) -> None:
        _, event = load_session_for_management(
            self._sessions, self._events, self._access_policy, actor, session_id
        )
        self._sessions.delete(session_id)
        self._unit_of_work.commit()

        logger.info(
            "session_deleted",
            extra={"session_id": session_id, "event_id": event.id, "user_id": actor.user_id},
        )
