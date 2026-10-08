from typing import Any

import pytest
from flask.testing import FlaskClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.entities import Registration
from app.infrastructure.database.models import EventModel
from app.infrastructure.database.repositories import SqlAlchemyRegistrationRepository
from tests.integration.http.conftest import ApiUser

EVENTS_URL = "/api/events"
VALID_EVENT = {
    "name": "Python Conference",
    "description": "Talks and workshops",
    "location": "Bogota",
    "start_date": "2030-05-10T09:00:00+00:00",
    "end_date": "2030-05-10T18:00:00-05:00",
    "capacity": 150,
}


def _create(client: FlaskClient, user: ApiUser, **overrides: Any) -> Any:
    return client.post(EVENTS_URL, json={**VALID_EVENT, **overrides}, headers=user.headers)


def _create_id(client: FlaskClient, user: ApiUser, **overrides: Any) -> int:
    response = _create(client, user, **overrides)
    assert response.status_code == 201, response.get_json()
    event_id: int = response.get_json()["id"]
    return event_id


def _update(client: FlaskClient, user: ApiUser, event_id: int, **overrides: Any) -> Any:
    return client.put(
        f"{EVENTS_URL}/{event_id}", json={**VALID_EVENT, **overrides}, headers=user.headers
    )


def _publish(client: FlaskClient, user: ApiUser, event_id: int) -> None:
    assert _update(client, user, event_id, status="PUBLISHED").status_code == 200


class TestCreateEvent:
    @pytest.mark.parametrize("role", ["organizer", "admin"])
    def test_creates_draft_owned_by_the_caller(
        self, db_client: FlaskClient, request: pytest.FixtureRequest, role: str
    ) -> None:
        user: ApiUser = request.getfixturevalue(role)

        response = _create(db_client, user)
        body = response.get_json()

        assert response.status_code == 201
        assert body["status"] == "DRAFT"
        assert body["created_by"] == user.id
        assert body["name"] == "Python Conference"
        assert body["end_date"] == "2030-05-10T23:00:00+00:00"
        assert {"id", "created_at", "updated_at"} <= set(body)

    def test_attendee_is_forbidden(self, db_client: FlaskClient, attendee: ApiUser) -> None:
        response = _create(db_client, attendee)

        assert response.status_code == 403
        assert response.get_json() == {
            "message": "You do not have permission to perform this action"
        }

    def test_requires_authentication(self, db_client: FlaskClient) -> None:
        response = db_client.post(EVENTS_URL, json=VALID_EVENT)

        assert response.status_code == 401
        assert response.get_json() == {"message": "Missing bearer token"}

    def test_authentication_is_checked_before_payload_validation(
        self, db_client: FlaskClient
    ) -> None:
        assert db_client.post(EVENTS_URL, json={"capacity": "x"}).status_code == 401

    def test_rejects_invalid_token(self, db_client: FlaskClient) -> None:
        response = db_client.post(
            EVENTS_URL, json=VALID_EVENT, headers={"Authorization": "Bearer forged.token.value"}
        )

        assert response.status_code == 401
        assert response.get_json() == {"message": "Invalid or expired token"}

    @pytest.mark.parametrize("field", ["created_by", "id", "status", "created_at", "updated_at"])
    def test_rejects_server_managed_fields(
        self, db_client: FlaskClient, organizer: ApiUser, field: str
    ) -> None:
        response = _create(db_client, organizer, **{field: 999})

        assert response.status_code == 422
        assert response.get_json()["errors"]["json"][field] == ["Unknown field."]

    @pytest.mark.parametrize(
        ("overrides", "field"),
        [
            ({"capacity": "10"}, "capacity"),
            ({"capacity": 10.5}, "capacity"),
            ({"capacity": 1_000_001}, "capacity"),
            ({"capacity": None}, "capacity"),
            ({"name": "x" * 201}, "name"),
            ({"start_date": "2030-05-10T09:00:00"}, "start_date"),
            ({"end_date": "not-a-date"}, "end_date"),
        ],
    )
    def test_rejects_malformed_payload(
        self, db_client: FlaskClient, organizer: ApiUser, overrides: dict[str, Any], field: str
    ) -> None:
        response = _create(db_client, organizer, **overrides)

        assert response.status_code == 422
        assert field in response.get_json()["errors"]["json"]

    def test_rejects_missing_required_fields(
        self, db_client: FlaskClient, organizer: ApiUser
    ) -> None:
        response = db_client.post(EVENTS_URL, json={}, headers=organizer.headers)

        assert response.status_code == 422
        assert set(response.get_json()["errors"]["json"]) == {
            "name",
            "location",
            "start_date",
            "end_date",
            "capacity",
        }

    @pytest.mark.parametrize(
        ("overrides", "message"),
        [
            ({"capacity": 0}, "capacity must be greater than zero"),
            ({"capacity": -5}, "capacity must be greater than zero"),
            ({"name": "   "}, "name must not be blank"),
            ({"end_date": VALID_EVENT["start_date"]}, "Start must be before end"),
            ({"end_date": "2030-05-10T08:00:00+00:00"}, "Start must be before end"),
        ],
    )
    def test_rejects_business_rule_violations(
        self, db_client: FlaskClient, organizer: ApiUser, overrides: dict[str, Any], message: str
    ) -> None:
        response = _create(db_client, organizer, **overrides)

        assert response.status_code == 422
        assert response.get_json() == {"message": message}


class TestGetEvent:
    def test_published_event_is_public(self, db_client: FlaskClient, organizer: ApiUser) -> None:
        event_id = _create_id(db_client, organizer)
        _publish(db_client, organizer, event_id)

        response = db_client.get(f"{EVENTS_URL}/{event_id}")

        assert response.status_code == 200
        assert response.get_json()["status"] == "PUBLISHED"

    @pytest.mark.parametrize("viewer", [None, "attendee", "other_organizer"])
    def test_draft_is_hidden_from_non_managers(
        self,
        db_client: FlaskClient,
        organizer: ApiUser,
        request: pytest.FixtureRequest,
        viewer: str | None,
    ) -> None:
        event_id = _create_id(db_client, organizer)
        headers = request.getfixturevalue(viewer).headers if viewer else {}

        response = db_client.get(f"{EVENTS_URL}/{event_id}", headers=headers)

        assert response.status_code == 404
        assert response.get_json() == {"message": "Event not found"}

    @pytest.mark.parametrize("viewer", ["organizer", "admin"])
    def test_draft_is_visible_to_owner_and_admin(
        self,
        db_client: FlaskClient,
        organizer: ApiUser,
        request: pytest.FixtureRequest,
        viewer: str,
    ) -> None:
        event_id = _create_id(db_client, organizer)

        response = db_client.get(
            f"{EVENTS_URL}/{event_id}", headers=request.getfixturevalue(viewer).headers
        )

        assert response.status_code == 200
        assert response.get_json()["status"] == "DRAFT"

    def test_invalid_token_is_rejected_even_on_public_endpoint(
        self, db_client: FlaskClient
    ) -> None:
        response = db_client.get(f"{EVENTS_URL}/1", headers={"Authorization": "Bearer bad"})

        assert response.status_code == 401

    @pytest.mark.parametrize("event_id", ["999999", "abc", "-1", "2147483648", "1.5"])
    def test_unknown_or_invalid_ids_return_not_found(
        self, db_client: FlaskClient, event_id: str
    ) -> None:
        response = db_client.get(f"{EVENTS_URL}/{event_id}")

        assert response.status_code == 404
        assert "message" in response.get_json()


class TestUpdateEvent:
    def test_owner_updates_and_publishes(self, db_client: FlaskClient, organizer: ApiUser) -> None:
        event_id = _create_id(db_client, organizer)

        response = _update(
            db_client, organizer, event_id, name="Python Summit", capacity=80, status="PUBLISHED"
        )
        body = response.get_json()

        assert response.status_code == 200
        assert (body["name"], body["capacity"], body["status"]) == (
            "Python Summit",
            80,
            "PUBLISHED",
        )
        assert body["created_by"] == organizer.id

    def test_omitted_status_is_kept(self, db_client: FlaskClient, organizer: ApiUser) -> None:
        event_id = _create_id(db_client, organizer)

        assert _update(db_client, organizer, event_id).get_json()["status"] == "DRAFT"

    def test_admin_updates_any_event(
        self, db_client: FlaskClient, organizer: ApiUser, admin: ApiUser
    ) -> None:
        event_id = _create_id(db_client, organizer)

        response = _update(db_client, admin, event_id, location="Medellin")

        assert response.status_code == 200
        assert response.get_json()["location"] == "Medellin"
        assert response.get_json()["created_by"] == organizer.id

    def test_organizer_cannot_update_foreign_event(
        self, db_client: FlaskClient, organizer: ApiUser, other_organizer: ApiUser
    ) -> None:
        event_id = _create_id(db_client, organizer)

        response = _update(db_client, other_organizer, event_id, name="Hijacked")

        assert response.status_code == 403
        assert response.get_json() == {"message": "You can only manage your own events"}

    def test_attendee_cannot_update(
        self, db_client: FlaskClient, organizer: ApiUser, attendee: ApiUser
    ) -> None:
        event_id = _create_id(db_client, organizer)

        assert _update(db_client, attendee, event_id).status_code == 403

    def test_requires_authentication(self, db_client: FlaskClient) -> None:
        assert db_client.put(f"{EVENTS_URL}/1", json=VALID_EVENT).status_code == 401

    def test_missing_event(self, db_client: FlaskClient, admin: ApiUser) -> None:
        response = _update(db_client, admin, 999_999)

        assert response.status_code == 404
        assert response.get_json() == {"message": "Event not found"}

    @pytest.mark.parametrize("field", ["created_by", "id", "created_at"])
    def test_rejects_mass_assignment(
        self, db_client: FlaskClient, organizer: ApiUser, field: str
    ) -> None:
        event_id = _create_id(db_client, organizer)

        response = _update(db_client, organizer, event_id, **{field: 1})

        assert response.status_code == 422
        assert field in response.get_json()["errors"]["json"]

    @pytest.mark.parametrize(
        ("overrides", "status_code"),
        [
            ({"capacity": 0}, 422),
            ({"end_date": "2030-05-09T00:00:00+00:00"}, 422),
            ({"status": "ARCHIVED"}, 422),
            ({"status": "COMPLETED"}, 409),
        ],
    )
    def test_validates_changes(
        self,
        db_client: FlaskClient,
        organizer: ApiUser,
        overrides: dict[str, Any],
        status_code: int,
    ) -> None:
        event_id = _create_id(db_client, organizer)

        assert _update(db_client, organizer, event_id, **overrides).status_code == status_code

    @pytest.mark.parametrize(
        ("path", "allowed"),
        [
            (["PUBLISHED", "COMPLETED"], True),
            (["CANCELLED"], True),
            (["PUBLISHED", "CANCELLED"], True),
            (["PUBLISHED", "DRAFT"], False),
            (["CANCELLED", "PUBLISHED"], False),
            (["PUBLISHED", "COMPLETED", "PUBLISHED"], False),
        ],
    )
    def test_status_transitions(
        self, db_client: FlaskClient, organizer: ApiUser, path: list[str], allowed: bool
    ) -> None:
        event_id = _create_id(db_client, organizer)
        *setup, last = path
        for status in setup:
            assert _update(db_client, organizer, event_id, status=status).status_code == 200

        response = _update(db_client, organizer, event_id, status=last)

        assert response.status_code == (200 if allowed else 409)

    def test_cancelled_event_cannot_be_edited(
        self, db_client: FlaskClient, organizer: ApiUser
    ) -> None:
        event_id = _create_id(db_client, organizer)
        _update(db_client, organizer, event_id, status="CANCELLED")

        response = _update(db_client, organizer, event_id, name="Revived")

        assert response.status_code == 409
        assert response.get_json() == {
            "message": "Cancelled or completed events cannot be modified"
        }

    def test_capacity_cannot_drop_below_registrations(
        self, db_client: FlaskClient, db_session: Session, organizer: ApiUser, attendee: ApiUser
    ) -> None:
        event_id = _create_id(db_client, organizer)
        _publish(db_client, organizer, event_id)
        registrations = SqlAlchemyRegistrationRepository(db_session)
        registrations.add(Registration(user_id=attendee.id, event_id=event_id))
        registrations.add(Registration(user_id=organizer.id, event_id=event_id))
        db_session.commit()

        assert _update(db_client, organizer, event_id, capacity=1).status_code == 409
        assert _update(db_client, organizer, event_id, capacity=2).status_code == 200


class TestDeleteEvent:
    def test_draft_is_deleted(
        self, db_client: FlaskClient, db_session: Session, organizer: ApiUser
    ) -> None:
        event_id = _create_id(db_client, organizer)

        response = db_client.delete(f"{EVENTS_URL}/{event_id}", headers=organizer.headers)

        assert response.status_code == 204
        assert response.data == b""
        assert db_session.scalar(select(func.count()).select_from(EventModel)) == 0

    def test_published_event_is_cancelled_instead(
        self, db_client: FlaskClient, organizer: ApiUser, admin: ApiUser
    ) -> None:
        event_id = _create_id(db_client, organizer)
        _publish(db_client, organizer, event_id)

        response = db_client.delete(f"{EVENTS_URL}/{event_id}", headers=admin.headers)

        assert response.status_code == 200
        assert response.get_json()["status"] == "CANCELLED"
        assert db_client.get(f"{EVENTS_URL}/{event_id}").status_code == 404

    @pytest.mark.parametrize("path", [["CANCELLED"], ["PUBLISHED", "COMPLETED"]])
    def test_final_events_cannot_be_removed(
        self, db_client: FlaskClient, organizer: ApiUser, path: list[str]
    ) -> None:
        event_id = _create_id(db_client, organizer)
        for status in path:
            _update(db_client, organizer, event_id, status=status)

        response = db_client.delete(f"{EVENTS_URL}/{event_id}", headers=organizer.headers)

        assert response.status_code == 409
        assert response.get_json() == {"message": f"{path[-1]} events cannot be removed"}

    def test_organizer_cannot_delete_foreign_event(
        self, db_client: FlaskClient, organizer: ApiUser, other_organizer: ApiUser
    ) -> None:
        event_id = _create_id(db_client, organizer)

        response = db_client.delete(f"{EVENTS_URL}/{event_id}", headers=other_organizer.headers)

        assert response.status_code == 403
        assert (
            db_client.get(f"{EVENTS_URL}/{event_id}", headers=organizer.headers).status_code == 200
        )

    def test_attendee_cannot_delete(
        self, db_client: FlaskClient, organizer: ApiUser, attendee: ApiUser
    ) -> None:
        event_id = _create_id(db_client, organizer)

        assert (
            db_client.delete(f"{EVENTS_URL}/{event_id}", headers=attendee.headers).status_code
            == 403
        )

    def test_requires_authentication(self, db_client: FlaskClient) -> None:
        assert db_client.delete(f"{EVENTS_URL}/1").status_code == 401

    def test_missing_event(self, db_client: FlaskClient, admin: ApiUser) -> None:
        response = db_client.delete(f"{EVENTS_URL}/999999", headers=admin.headers)

        assert response.status_code == 404


class TestListingVisibility:
    def test_listing_depends_on_role(
        self,
        db_client: FlaskClient,
        organizer: ApiUser,
        other_organizer: ApiUser,
        admin: ApiUser,
        attendee: ApiUser,
    ) -> None:
        _create_id(db_client, organizer, name="Mine draft")
        published = _create_id(db_client, other_organizer, name="Public event")
        _update(db_client, other_organizer, published, name="Public event", status="PUBLISHED")
        _create_id(db_client, other_organizer, name="Foreign draft")

        def names(headers: dict[str, str]) -> set[str]:
            items = db_client.get(EVENTS_URL, headers=headers).get_json()["items"]
            return {item["name"] for item in items}

        assert names({}) == {"Public event"}
        assert names(attendee.headers) == {"Public event"}
        assert names(organizer.headers) == {"Public event", "Mine draft"}
        assert names(admin.headers) == {"Public event", "Mine draft", "Foreign draft"}

    def test_status_filter(self, db_client: FlaskClient, organizer: ApiUser) -> None:
        _create_id(db_client, organizer, name="Draft one")

        drafts = db_client.get(f"{EVENTS_URL}?status=DRAFT", headers=organizer.headers)
        anonymous = db_client.get(f"{EVENTS_URL}?status=DRAFT")

        assert [item["name"] for item in drafts.get_json()["items"]] == ["Draft one"]
        assert anonymous.get_json()["items"] == []
        assert db_client.get(f"{EVENTS_URL}?status=UNKNOWN").status_code == 422

    def test_invalid_token_on_listing_is_rejected(self, db_client: FlaskClient) -> None:
        response = db_client.get(EVENTS_URL, headers={"Authorization": "Bearer bad"})

        assert response.status_code == 401
