from datetime import timedelta
from typing import Any

import pytest

from app.domain.entities import Event
from app.domain.enums import EventRemoval, EventStatus
from app.domain.exceptions import (
    EventCannotBeRemovedError,
    EventCapacityBelowRegistrationsError,
    EventNotEditableError,
    InvalidEventStatusTransitionError,
    InvalidValueError,
)
from tests.factories import EVENT_START, build_event

ALLOWED_TRANSITIONS = {
    (EventStatus.DRAFT, EventStatus.PUBLISHED),
    (EventStatus.DRAFT, EventStatus.CANCELLED),
    (EventStatus.PUBLISHED, EventStatus.CANCELLED),
    (EventStatus.PUBLISHED, EventStatus.COMPLETED),
}
ALL_CHANGES = [
    (source, target) for source in EventStatus for target in EventStatus if source is not target
]


def _details(event: Event, **overrides: Any) -> dict[str, Any]:
    values: dict[str, Any] = {
        "name": event.name,
        "description": event.description,
        "location": event.location,
        "start_date": event.start_date,
        "end_date": event.end_date,
        "capacity": event.capacity,
        "registered_count": 0,
    }
    values.update(overrides)
    return values


class TestStatusTransitions:
    @pytest.mark.parametrize(("source", "target"), sorted(ALLOWED_TRANSITIONS))
    def test_allowed_transitions(self, source: EventStatus, target: EventStatus) -> None:
        event = build_event(status=source)

        changed = event.with_status(target)

        assert changed.status is target
        assert event.status is source

    @pytest.mark.parametrize(
        ("source", "target"), [pair for pair in ALL_CHANGES if pair not in ALLOWED_TRANSITIONS]
    )
    def test_forbidden_transitions(self, source: EventStatus, target: EventStatus) -> None:
        with pytest.raises(InvalidEventStatusTransitionError, match=f"{source} to {target}"):
            build_event(status=source).with_status(target)

    @pytest.mark.parametrize("status", list(EventStatus))
    def test_keeping_the_same_status_is_a_no_op(self, status: EventStatus) -> None:
        event = build_event(status=status)

        assert event.with_status(status) is event

    @pytest.mark.parametrize(
        ("status", "is_final"),
        [
            (EventStatus.DRAFT, False),
            (EventStatus.PUBLISHED, False),
            (EventStatus.CANCELLED, True),
            (EventStatus.COMPLETED, True),
        ],
    )
    def test_cancelled_and_completed_are_final(self, status: EventStatus, is_final: bool) -> None:
        assert status.is_final is is_final


class TestEventDetailsUpdate:
    def test_returns_updated_copy_keeping_identity_and_owner(self) -> None:
        event = build_event(id=7, created_by=3, status=EventStatus.DRAFT)

        updated = event.with_details(**_details(event, name="  Renamed  ", capacity=50))

        assert (updated.id, updated.created_by, updated.status) == (7, 3, EventStatus.DRAFT)
        assert (updated.name, updated.capacity) == ("Renamed", 50)
        assert event.name == "PyCon Colombia"

    @pytest.mark.parametrize(
        "overrides",
        [
            {"name": "   "},
            {"location": ""},
            {"capacity": 0},
            {"capacity": -1},
            {"end_date": EVENT_START},
            {"end_date": EVENT_START - timedelta(hours=1)},
        ],
    )
    def test_revalidates_invariants(self, overrides: dict[str, Any]) -> None:
        event = build_event()

        with pytest.raises(InvalidValueError):
            event.with_details(**_details(event, **overrides))

    @pytest.mark.parametrize("status", [EventStatus.CANCELLED, EventStatus.COMPLETED])
    def test_final_events_cannot_be_edited(self, status: EventStatus) -> None:
        event = build_event(status=status)

        with pytest.raises(EventNotEditableError):
            event.with_details(**_details(event))

    def test_capacity_cannot_drop_below_registered_attendees(self) -> None:
        event = build_event(capacity=100)

        with pytest.raises(EventCapacityBelowRegistrationsError):
            event.with_details(**_details(event, capacity=9, registered_count=10))

    def test_capacity_can_match_registered_attendees(self) -> None:
        event = build_event(capacity=100)

        assert (
            event.with_details(**_details(event, capacity=10, registered_count=10)).capacity == 10
        )


class TestRemoval:
    @pytest.mark.parametrize(
        ("status", "action"),
        [(EventStatus.DRAFT, EventRemoval.DELETE), (EventStatus.PUBLISHED, EventRemoval.CANCEL)],
    )
    def test_removal_action_depends_on_status(
        self, status: EventStatus, action: EventRemoval
    ) -> None:
        assert build_event(status=status).removal_action() is action

    @pytest.mark.parametrize("status", [EventStatus.CANCELLED, EventStatus.COMPLETED])
    def test_final_events_cannot_be_removed(self, status: EventStatus) -> None:
        with pytest.raises(EventCannotBeRemovedError, match=status.value):
            build_event(status=status).removal_action()


class TestOwnershipAndVisibility:
    def test_ownership_is_based_on_creator(self) -> None:
        event = build_event(created_by=5)

        assert event.is_owned_by(5)
        assert not event.is_owned_by(6)

    @pytest.mark.parametrize("status", list(EventStatus))
    def test_only_published_events_are_publicly_visible(self, status: EventStatus) -> None:
        assert build_event(status=status).is_publicly_visible is (status is EventStatus.PUBLISHED)
