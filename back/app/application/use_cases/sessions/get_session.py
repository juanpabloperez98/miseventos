from app.application.dto import Actor
from app.application.services import EventAccessPolicy
from app.domain.entities import Session
from app.domain.exceptions import NotFoundError
from app.domain.ports import EventRepository, SessionRepository


class GetSessionUseCase:
    def __init__(
        self,
        sessions: SessionRepository,
        events: EventRepository,
        access_policy: EventAccessPolicy,
    ) -> None:
        self._sessions = sessions
        self._events = events
        self._access_policy = access_policy

    def execute(self, session_id: int, actor: Actor | None = None) -> Session:
        session = self._sessions.get_by_id(session_id)
        event = self._events.get_by_id(session.event_id) if session is not None else None
        if session is None or event is None or not self._access_policy.can_view(actor, event):
            raise NotFoundError.for_entity("Session")
        return session
