from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ListEventsQuery:
    search: str | None = None
    page: int = 1
    per_page: int = 10
