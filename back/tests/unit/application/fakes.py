from dataclasses import replace
from datetime import UTC, datetime

from app.domain.entities import User
from app.domain.ports import UnitOfWork, UserRepository


class InMemoryUserRepository(UserRepository):
    def __init__(self) -> None:
        self._users: dict[int, User] = {}

    def add(self, user: User) -> User:
        now = datetime.now(UTC)
        stored = replace(user, id=len(self._users) + 1, created_at=now, updated_at=now)
        self._users[stored.id or 0] = stored
        return stored

    def get_by_id(self, user_id: int) -> User | None:
        return self._users.get(user_id)

    def get_by_email(self, email: str) -> User | None:
        return next((user for user in self._users.values() if user.email == email), None)


class SpyUnitOfWork(UnitOfWork):
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1
