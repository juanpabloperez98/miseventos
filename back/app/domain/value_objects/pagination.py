import math
from collections.abc import Sequence
from dataclasses import dataclass

from app.domain.exceptions import InvalidValueError

MAX_PER_PAGE = 100


@dataclass(frozen=True, slots=True)
class PageRequest:
    page: int = 1
    per_page: int = 10

    def __post_init__(self) -> None:
        if self.page < 1:
            raise InvalidValueError("Page must be greater than or equal to 1")
        if not 1 <= self.per_page <= MAX_PER_PAGE:
            raise InvalidValueError(f"Items per page must be between 1 and {MAX_PER_PAGE}")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.per_page


@dataclass(frozen=True, slots=True)
class Page[T]:
    items: Sequence[T]
    total: int
    request: PageRequest

    @property
    def page(self) -> int:
        return self.request.page

    @property
    def per_page(self) -> int:
        return self.request.per_page

    @property
    def pages(self) -> int:
        return math.ceil(self.total / self.request.per_page)
