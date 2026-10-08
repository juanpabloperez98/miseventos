from abc import ABC, abstractmethod

from app.domain.entities import User


class UserRepository(ABC):
    @abstractmethod
    def add(self, user: User) -> User: ...

    @abstractmethod
    def get_by_id(self, user_id: int) -> User | None: ...

    @abstractmethod
    def get_by_email(self, email: str) -> User | None: ...
