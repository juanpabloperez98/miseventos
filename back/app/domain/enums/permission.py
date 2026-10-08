from enum import StrEnum


class Permission(StrEnum):
    MANAGE_EVENTS = "events:manage"
    MANAGE_ANY_EVENT = "events:manage_any"
    MANAGE_SESSIONS = "sessions:manage"
    MANAGE_SPEAKERS = "speakers:manage"
    REGISTER_TO_EVENTS = "registrations:create"
