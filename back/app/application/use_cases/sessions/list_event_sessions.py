from app.application.dto import Actor
from app.application.use_cases.events.get_event import GetEventUseCase
from app.domain.entities import Session
from app.domain.ports import SessionRepository


class ListEventSessionsUseCase:
    def __init__(self, sessions: SessionRepository, get_event: GetEventUseCase) -> None:
        self._sessions = sessions
        self._get_event = get_event

    def execute(self, event_id: int, actor: Actor | None = None) -> list[Session]:
        self._get_event.execute(event_id, actor)
        return self._sessions.list_by_event(event_id)
