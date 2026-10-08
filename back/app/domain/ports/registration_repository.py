from abc import ABC, abstractmethod

from app.domain.entities import Registration


class RegistrationRepository(ABC):
    @abstractmethod
    def add(self, registration: Registration) -> Registration: ...

    @abstractmethod
    def get(self, user_id: int, event_id: int) -> Registration | None: ...

    @abstractmethod
    def delete(self, registration_id: int) -> None: ...

    @abstractmethod
    def count_by_event(self, event_id: int) -> int: ...
