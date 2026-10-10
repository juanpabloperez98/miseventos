from collections.abc import Sequence

from app.application.dto import SessionView
from app.domain.entities import Session
from app.domain.ports import SpeakerRepository


def to_session_views(sessions: Sequence[Session], speakers: SpeakerRepository) -> list[SessionView]:
    speaker_ids = {session.speaker_id for session in sessions if session.speaker_id is not None}
    names: dict[int, str] = {}
    for speaker_id in speaker_ids:
        speaker = speakers.get_by_id(speaker_id)
        if speaker is not None:
            names[speaker_id] = speaker.name
    return [
        SessionView.from_session(
            session, names.get(session.speaker_id) if session.speaker_id is not None else None
        )
        for session in sessions
    ]


def to_session_view(session: Session, speakers: SpeakerRepository) -> SessionView:
    return to_session_views([session], speakers)[0]
