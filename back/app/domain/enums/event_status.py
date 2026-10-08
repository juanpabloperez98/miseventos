from enum import StrEnum


class EventStatus(StrEnum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"

    @property
    def is_final(self) -> bool:
        return not _ALLOWED_TRANSITIONS[self]

    def can_transition_to(self, target: "EventStatus") -> bool:
        return target in _ALLOWED_TRANSITIONS[self]


_ALLOWED_TRANSITIONS: dict[EventStatus, frozenset[EventStatus]] = {
    EventStatus.DRAFT: frozenset({EventStatus.PUBLISHED, EventStatus.CANCELLED}),
    EventStatus.PUBLISHED: frozenset({EventStatus.CANCELLED, EventStatus.COMPLETED}),
    EventStatus.CANCELLED: frozenset(),
    EventStatus.COMPLETED: frozenset(),
}
