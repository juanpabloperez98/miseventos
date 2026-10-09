from datetime import timedelta

import pytest

from app.domain.entities import Session, Speaker
from app.domain.enums import EventStatus, UserRole
from app.domain.exceptions import (
    EventCapacityExceededError,
    EventNotOpenForRegistrationError,
    InvalidValueError,
)
from tests.factories import EVENT_START, build_event, build_session, build_user


class TestUser:
    def test_defaults_to_attendee_and_normalizes_email(self) -> None:
        user = build_user(email=" Ada@Example.com ", role=UserRole.ATTENDEE)

        assert user.email == "ada@example.com"
        assert user.role is UserRole.ATTENDEE

    def test_rejects_blank_name(self) -> None:
        with pytest.raises(InvalidValueError, match="name"):
            build_user(name="   ")


class TestEvent:
    def test_new_events_start_as_draft(self) -> None:
        event = build_event(status=EventStatus.DRAFT)

        assert event.status is EventStatus.DRAFT
        assert not event.is_open_for_registration

    @pytest.mark.parametrize("capacity", [0, -5])
    def test_rejects_non_positive_capacity(self, capacity: int) -> None:
        with pytest.raises(InvalidValueError, match="capacity"):
            build_event(capacity=capacity)

    def test_rejects_end_date_before_start_date(self) -> None:
        with pytest.raises(InvalidValueError):
            build_event(start_date=EVENT_START, end_date=EVENT_START - timedelta(hours=1))

    def test_blank_description_is_stored_as_none(self) -> None:
        assert build_event(description="  ").description is None

    def test_accepts_registration_when_published_with_free_seats(self) -> None:
        build_event(capacity=2).ensure_can_accept_registration(registered_count=1)

    def test_rejects_registration_when_full(self) -> None:
        with pytest.raises(EventCapacityExceededError):
            build_event(capacity=2).ensure_can_accept_registration(registered_count=2)

    @pytest.mark.parametrize(
        "status", [EventStatus.DRAFT, EventStatus.CANCELLED, EventStatus.COMPLETED]
    )
    def test_rejects_registration_when_not_published(self, status: EventStatus) -> None:
        with pytest.raises(EventNotOpenForRegistrationError):
            build_event(status=status).ensure_can_accept_registration(registered_count=0)


class TestSession:
    def test_rejects_start_time_after_end_time(self) -> None:
        with pytest.raises(InvalidValueError):
            build_session(start_time=EVENT_START + timedelta(hours=2), end_time=EVENT_START)

    def test_rejects_non_positive_capacity(self) -> None:
        with pytest.raises(InvalidValueError, match="capacity"):
            build_session(capacity=0)

    def test_capacity_is_required(self) -> None:
        values = {"event_id": 1, "title": "Talk", "start_time": EVENT_START}

        with pytest.raises(TypeError, match="capacity"):
            Session(**values, end_time=EVENT_START + timedelta(hours=1))  # type: ignore[call-arg]

    def test_fits_within_event_schedule(self) -> None:
        build_session().ensure_fits_within(build_event())

    def test_rejects_session_outside_event_schedule(self) -> None:
        session = build_session(
            start_time=EVENT_START - timedelta(hours=1), end_time=EVENT_START + timedelta(hours=1)
        )

        with pytest.raises(InvalidValueError, match="within the event"):
            session.ensure_fits_within(build_event())

    @pytest.mark.parametrize("capacity", [1, 99, 100])
    def test_capacity_up_to_the_event_capacity_fits(self, capacity: int) -> None:
        build_session(capacity=capacity).ensure_fits_within(build_event(capacity=100))

    @pytest.mark.parametrize("capacity", [101, 500])
    def test_rejects_capacity_above_the_event_capacity(self, capacity: int) -> None:
        with pytest.raises(InvalidValueError, match="cannot exceed the event capacity"):
            build_session(capacity=capacity).ensure_fits_within(build_event(capacity=100))


class TestSessionDetailsUpdate:
    def test_returns_revalidated_copy_keeping_identity_and_event(self) -> None:
        session = build_session(id=3, event_id=7, speaker_id=2)

        updated = session.with_details(
            title="  New title  ",
            description=None,
            start_time=session.start_time,
            end_time=session.end_time,
            capacity=5,
            speaker_id=None,
        )

        assert (updated.id, updated.event_id) == (3, 7)
        assert (updated.title, updated.capacity, updated.speaker_id) == ("New title", 5, None)
        assert session.title == "Hexagonal architecture in Python"

    @pytest.mark.parametrize(
        "overrides",
        [{"capacity": 0}, {"title": " "}, {"end_time": EVENT_START + timedelta(hours=1)}],
    )
    def test_rejects_invalid_changes(self, overrides: dict[str, object]) -> None:
        session = build_session()
        values: dict[str, object] = {
            "title": session.title,
            "description": session.description,
            "start_time": session.start_time,
            "end_time": session.end_time,
            "capacity": session.capacity,
            "speaker_id": session.speaker_id,
            **overrides,
        }

        with pytest.raises(InvalidValueError):
            session.with_details(**values)  # type: ignore[arg-type]


class TestSpeaker:
    def test_email_is_optional_and_normalized(self) -> None:
        assert Speaker(name="Grace").email is None
        assert Speaker(name="Grace", email="Grace@Navy.mil").email == "grace@navy.mil"

    def test_rejects_invalid_email(self) -> None:
        with pytest.raises(InvalidValueError):
            Speaker(name="Grace", email="not-an-email")
