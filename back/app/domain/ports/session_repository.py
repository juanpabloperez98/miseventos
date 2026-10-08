from abc import ABC, abstractmethod

from app.domain.entities import Session


class SessionRepository(ABC):
    @abstractmethod
    def add(self, session: Session) -> Session: ...

    @abstractmethod
    def get_by_id(self, session_id: int) -> Session | None: ...

    @abstractmethod
    def update(self, session: Session) -> Session: ...

    @abstractmethod
    def delete(self, session_id: int) -> None: ...

    @abstractmethod
    def list_by_event(self, event_id: int) -> list[Session]: ...
