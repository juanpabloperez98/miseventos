from app.application.dto import Actor, SessionView
from app.application.use_cases.events.get_event import GetEventUseCase
from app.application.use_cases.sessions._session_views import to_session_views
from app.domain.ports import SessionRepository, SpeakerRepository


class ListEventSessionsUseCase:
    def __init__(
        self,
        sessions: SessionRepository,
        speakers: SpeakerRepository,
        get_event: GetEventUseCase,
    ) -> None:
        self._sessions = sessions
        self._speakers = speakers
        self._get_event = get_event

    def execute(self, event_id: int, actor: Actor | None = None) -> list[SessionView]:
        self._get_event.execute(event_id, actor)
        return to_session_views(self._sessions.list_by_event(event_id), self._speakers)
