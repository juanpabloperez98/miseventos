from app.application.dto import Actor
from app.application.services import EventAccessPolicy
from app.application.use_cases.events._managed_event import load_event_for_management
from app.domain.entities import Event, Session
from app.domain.exceptions import NotFoundError
from app.domain.ports import EventRepository, SessionRepository, SpeakerRepository


def load_event_for_session_management(
    events: EventRepository, access_policy: EventAccessPolicy, actor: Actor, event_id: int
) -> Event:
    access_policy.ensure_can_manage_sessions(actor)
    return _load_editable_event(events, access_policy, actor, event_id)


def load_session_for_management(
    sessions: SessionRepository,
    events: EventRepository,
    access_policy: EventAccessPolicy,
    actor: Actor,
    session_id: int,
) -> tuple[Session, Event]:
    access_policy.ensure_can_manage_sessions(actor)
    session = sessions.get_by_id(session_id)
    if session is None:
        raise NotFoundError.for_entity("Session")
    return session, _load_editable_event(events, access_policy, actor, session.event_id)


def ensure_speaker_exists(speakers: SpeakerRepository, speaker_id: int | None) -> None:
    if speaker_id is not None and speakers.get_by_id(speaker_id) is None:
        raise NotFoundError.for_entity("Speaker")


def _load_editable_event(
    events: EventRepository, access_policy: EventAccessPolicy, actor: Actor, event_id: int
) -> Event:
    event = load_event_for_management(events, access_policy, actor, event_id)
    event.ensure_editable()
    return event
