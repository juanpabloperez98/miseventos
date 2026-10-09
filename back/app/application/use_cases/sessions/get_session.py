from app.application.dto import Actor, SessionView
from app.application.services import EventAccessPolicy
from app.application.use_cases.sessions._session_views import to_session_view
from app.domain.exceptions import NotFoundError
from app.domain.ports import EventRepository, SessionRepository, SpeakerRepository


class GetSessionUseCase:
    def __init__(
        self,
        sessions: SessionRepository,
        events: EventRepository,
        speakers: SpeakerRepository,
        access_policy: EventAccessPolicy,
    ) -> None:
        self._sessions = sessions
        self._events = events
        self._speakers = speakers
        self._access_policy = access_policy

    def execute(self, session_id: int, actor: Actor | None = None) -> SessionView:
        session = self._sessions.get_by_id(session_id)
        event = self._events.get_by_id(session.event_id) if session is not None else None
        if session is None or event is None or not self._access_policy.can_view(actor, event):
            raise NotFoundError.for_entity("Session")
        return to_session_view(session, self._speakers)
