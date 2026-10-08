from typing import Any

import pytest
from flask.testing import FlaskClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.enums import UserRole
from app.infrastructure.database.models import RegistrationModel
from tests.integration.http.conftest import ApiUser, UserFactory

EVENT = {
    "name": "Python Conference",
    "location": "Bogota",
    "start_date": "2030-05-10T10:00:00+00:00",
    "end_date": "2030-05-10T18:00:00+00:00",
    "capacity": 2,
}


def _create_event(
    client: FlaskClient, owner: ApiUser, status: str | None = "PUBLISHED", **overrides: Any
) -> int:
    payload = {**EVENT, **overrides}
    response = client.post("/api/events", json=payload, headers=owner.headers)
    assert response.status_code == 201, response.get_json()
    event_id: int = response.get_json()["id"]
    for step in {
        "PUBLISHED": ["PUBLISHED"],
        "CANCELLED": ["CANCELLED"],
        "COMPLETED": ["PUBLISHED", "COMPLETED"],
    }.get(status or "", []):
        update = client.put(
            f"/api/events/{event_id}", json={**payload, "status": step}, headers=owner.headers
        )
        assert update.status_code == 200, update.get_json()
    return event_id


def _register(client: FlaskClient, user: ApiUser | None, target_event_id: int, **body: Any) -> Any:
    headers = user.headers if user else {}
    return client.post(
        f"/api/events/{target_event_id}/registrations", json=body or None, headers=headers
    )


def _my_events(client: FlaskClient, user: ApiUser) -> list[dict[str, Any]]:
    response = client.get("/api/me/registrations", headers=user.headers)
    assert response.status_code == 200
    items: list[dict[str, Any]] = response.get_json()
    return items


def _registration_count(db_session: Session, event_id: int) -> int:
    statement = select(func.count()).where(RegistrationModel.event_id == event_id)
    return db_session.scalar(statement) or 0


class TestRegisterForEvent:
    def test_registers_authenticated_user(
        self, db_client: FlaskClient, organizer: ApiUser, attendee: ApiUser
    ) -> None:
        event_id = _create_event(db_client, organizer)

        response = _register(db_client, attendee, event_id)
        body = response.get_json()

        assert response.status_code == 201
        assert (body["user_id"], body["event_id"]) == (attendee.id, event_id)
        assert {"id", "registered_at"} <= set(body)

    def test_empty_json_body_is_accepted(
        self, db_client: FlaskClient, organizer: ApiUser, attendee: ApiUser
    ) -> None:
        event_id = _create_event(db_client, organizer)

        response = db_client.post(
            f"/api/events/{event_id}/registrations", json={}, headers=attendee.headers
        )

        assert response.status_code == 201

    @pytest.mark.parametrize("field", ["user_id", "event_id", "id"])
    def test_body_cannot_choose_the_registered_user(
        self,
        db_client: FlaskClient,
        db_session: Session,
        organizer: ApiUser,
        attendee: ApiUser,
        field: str,
    ) -> None:
        event_id = _create_event(db_client, organizer)

        response = _register(db_client, attendee, event_id, **{field: organizer.id})

        assert response.status_code == 422
        assert response.get_json()["errors"]["json"][field] == ["Unknown field."]
        assert _registration_count(db_session, event_id) == 0

    def test_registered_user_comes_from_the_token(
        self,
        db_client: FlaskClient,
        organizer: ApiUser,
        attendee: ApiUser,
        make_api_user: UserFactory,
    ) -> None:
        other = make_api_user(UserRole.ATTENDEE, "other.attendee@example.com")
        event_id = _create_event(db_client, organizer)

        _register(db_client, other, event_id)

        assert [item["id"] for item in _my_events(db_client, other)] == [event_id]
        assert _my_events(db_client, attendee) == []

    def test_requires_authentication(
        self, db_client: FlaskClient, db_session: Session, organizer: ApiUser
    ) -> None:
        event_id = _create_event(db_client, organizer)

        response = _register(db_client, None, event_id)

        assert response.status_code == 401
        assert response.get_json() == {"message": "Missing bearer token"}
        assert _registration_count(db_session, event_id) == 0

    def test_rejects_invalid_token(self, db_client: FlaskClient, organizer: ApiUser) -> None:
        event_id = _create_event(db_client, organizer)

        response = db_client.post(
            f"/api/events/{event_id}/registrations", headers={"Authorization": "Bearer bad"}
        )

        assert response.status_code == 401

    def test_unknown_event(self, db_client: FlaskClient, attendee: ApiUser) -> None:
        response = _register(db_client, attendee, 999_999)

        assert response.status_code == 404
        assert response.get_json() == {"message": "Event not found"}

    @pytest.mark.parametrize("raw_id", ["abc", "-1", "2147483648"])
    def test_invalid_event_ids(
        self, db_client: FlaskClient, attendee: ApiUser, raw_id: str
    ) -> None:
        response = db_client.post(f"/api/events/{raw_id}/registrations", headers=attendee.headers)

        assert response.status_code == 404

    @pytest.mark.parametrize("status", ["DRAFT", "CANCELLED", "COMPLETED"])
    def test_events_hidden_from_the_user_answer_not_found(
        self, db_client: FlaskClient, organizer: ApiUser, attendee: ApiUser, status: str
    ) -> None:
        event_id = _create_event(db_client, organizer, status=status if status != "DRAFT" else None)

        response = _register(db_client, attendee, event_id)

        assert response.status_code == 404
        assert response.get_json() == {"message": "Event not found"}

    @pytest.mark.parametrize("status", ["DRAFT", "CANCELLED", "COMPLETED"])
    def test_visible_events_not_open_for_registration_conflict(
        self, db_client: FlaskClient, organizer: ApiUser, status: str
    ) -> None:
        event_id = _create_event(db_client, organizer, status=status if status != "DRAFT" else None)

        response = _register(db_client, organizer, event_id)

        assert response.status_code == 409
        assert response.get_json() == {"message": "Event is not open for registration"}

    def test_duplicate_registration_conflicts(
        self, db_client: FlaskClient, db_session: Session, organizer: ApiUser, attendee: ApiUser
    ) -> None:
        event_id = _create_event(db_client, organizer)
        _register(db_client, attendee, event_id)

        response = _register(db_client, attendee, event_id)

        assert response.status_code == 409
        assert response.get_json() == {"message": "User is already registered to this event"}
        assert _registration_count(db_session, event_id) == 1


class TestCapacity:
    def test_seats_are_granted_until_capacity_is_reached(
        self,
        db_client: FlaskClient,
        db_session: Session,
        organizer: ApiUser,
        make_api_user: UserFactory,
    ) -> None:
        event_id = _create_event(db_client, organizer, capacity=2)
        users = [make_api_user(UserRole.ATTENDEE, f"seat{index}@example.com") for index in range(3)]

        first, last_seat, over = (_register(db_client, user, event_id) for user in users)

        assert (first.status_code, last_seat.status_code) == (201, 201)
        assert over.status_code == 409
        assert over.get_json() == {"message": "Event has reached its capacity"}
        assert _registration_count(db_session, event_id) == 2


class TestMyRegistrations:
    def test_lists_registered_events_with_event_details(
        self,
        db_client: FlaskClient,
        organizer: ApiUser,
        attendee: ApiUser,
    ) -> None:
        later = _create_event(
            db_client,
            organizer,
            name="Later",
            start_date="2030-06-01T10:00:00+00:00",
            end_date="2030-06-01T12:00:00+00:00",
        )
        sooner = _create_event(db_client, organizer, name="Sooner")
        _create_event(db_client, organizer, name="Not registered")
        _register(db_client, attendee, later)
        _register(db_client, attendee, sooner)

        items = _my_events(db_client, attendee)

        assert [(item["id"], item["name"]) for item in items] == [
            (sooner, "Sooner"),
            (later, "Later"),
        ]
        assert {"location", "start_date", "capacity", "status"} <= set(items[0])

    def test_user_without_registrations_gets_empty_list(
        self, db_client: FlaskClient, attendee: ApiUser
    ) -> None:
        assert _my_events(db_client, attendee) == []

    def test_users_only_see_their_own_registrations(
        self,
        db_client: FlaskClient,
        organizer: ApiUser,
        attendee: ApiUser,
        make_api_user: UserFactory,
    ) -> None:
        other = make_api_user(UserRole.ATTENDEE, "other@example.com")
        mine = _create_event(db_client, organizer, name="Mine")
        theirs = _create_event(db_client, organizer, name="Theirs")
        _register(db_client, attendee, mine)
        _register(db_client, other, theirs)

        response = db_client.get(
            f"/api/me/registrations?user_id={other.id}", headers=attendee.headers
        )

        assert [item["id"] for item in response.get_json()] == [mine]
        assert [item["id"] for item in _my_events(db_client, other)] == [theirs]

    def test_history_keeps_events_cancelled_after_registration(
        self, db_client: FlaskClient, organizer: ApiUser, attendee: ApiUser
    ) -> None:
        event_id = _create_event(db_client, organizer)
        _register(db_client, attendee, event_id)
        db_client.delete(f"/api/events/{event_id}", headers=organizer.headers)

        assert [(item["id"], item["status"]) for item in _my_events(db_client, attendee)] == [
            (event_id, "CANCELLED")
        ]

    def test_requires_authentication(self, db_client: FlaskClient) -> None:
        assert db_client.get("/api/me/registrations").status_code == 401
        assert (
            db_client.get(
                "/api/me/registrations", headers={"Authorization": "Bearer bad"}
            ).status_code
            == 401
        )
