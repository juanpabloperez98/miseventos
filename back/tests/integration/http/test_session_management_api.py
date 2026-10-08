from typing import Any

import pytest
from flask.testing import FlaskClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.entities import Speaker
from app.infrastructure.database.models import SessionModel
from app.infrastructure.database.repositories import SqlAlchemySpeakerRepository
from tests.integration.http.conftest import ApiUser

EVENT = {
    "name": "Python Conference",
    "description": "Talks and workshops",
    "location": "Bogota",
    "start_date": "2030-05-10T10:00:00+00:00",
    "end_date": "2030-05-10T18:00:00+00:00",
    "capacity": 150,
}
SESSION = {
    "title": "Clean architecture",
    "description": "Ports and adapters",
    "start_time": "2030-05-10T11:00:00+00:00",
    "end_time": "2030-05-10T12:00:00+00:00",
    "capacity": 40,
}


def _create_event(client: FlaskClient, user: ApiUser, publish: bool = False) -> int:
    response = client.post("/api/events", json=EVENT, headers=user.headers)
    assert response.status_code == 201, response.get_json()
    event_id: int = response.get_json()["id"]
    if publish:
        _set_event_status(client, user, event_id, "PUBLISHED")
    return event_id


def _set_event_status(client: FlaskClient, user: ApiUser, event_id: int, status: str) -> None:
    response = client.put(
        f"/api/events/{event_id}", json={**EVENT, "status": status}, headers=user.headers
    )
    assert response.status_code == 200, response.get_json()


def _create_session(
    client: FlaskClient, user: ApiUser | None, target_event_id: int, **overrides: Any
) -> Any:
    headers = user.headers if user else {}
    return client.post(
        f"/api/events/{target_event_id}/sessions", json={**SESSION, **overrides}, headers=headers
    )


def _create_session_id(client: FlaskClient, user: ApiUser, event_id: int, **overrides: Any) -> int:
    response = _create_session(client, user, event_id, **overrides)
    assert response.status_code == 201, response.get_json()
    session_id: int = response.get_json()["id"]
    return session_id


def _update_session(client: FlaskClient, user: ApiUser, session_id: int, **overrides: Any) -> Any:
    return client.put(
        f"/api/sessions/{session_id}", json={**SESSION, **overrides}, headers=user.headers
    )


@pytest.fixture
def speaker_id(db_session: Session) -> int:
    speaker = SqlAlchemySpeakerRepository(db_session).add(Speaker(name="Grace Hopper"))
    db_session.commit()
    assert speaker.id is not None
    return speaker.id


@pytest.fixture
def event_id(db_client: FlaskClient, organizer: ApiUser) -> int:
    return _create_event(db_client, organizer)


class TestCreateSession:
    @pytest.mark.parametrize("role", ["organizer", "admin"])
    def test_creates_session_without_speaker(
        self,
        db_client: FlaskClient,
        request: pytest.FixtureRequest,
        event_id: int,
        role: str,
    ) -> None:
        response = _create_session(db_client, request.getfixturevalue(role), event_id)
        body = response.get_json()

        assert response.status_code == 201
        assert body["event_id"] == event_id
        assert body["speaker_id"] is None
        assert (body["title"], body["capacity"]) == ("Clean architecture", 40)
        assert {"id", "created_at", "updated_at"} <= set(body)

    def test_creates_session_with_speaker(
        self, db_client: FlaskClient, organizer: ApiUser, event_id: int, speaker_id: int
    ) -> None:
        response = _create_session(db_client, organizer, event_id, speaker_id=speaker_id)

        assert response.status_code == 201
        assert response.get_json()["speaker_id"] == speaker_id

    def test_dates_are_normalized_to_utc(
        self, db_client: FlaskClient, organizer: ApiUser, event_id: int
    ) -> None:
        response = _create_session(
            db_client,
            organizer,
            event_id,
            start_time="2030-05-10T08:00:00-05:00",
            end_time="2030-05-10T09:30:00-05:00",
        )

        assert response.status_code == 201
        assert response.get_json()["start_time"] == "2030-05-10T13:00:00+00:00"

    def test_session_may_span_the_whole_event(
        self, db_client: FlaskClient, organizer: ApiUser, event_id: int
    ) -> None:
        response = _create_session(
            db_client,
            organizer,
            event_id,
            start_time=EVENT["start_date"],
            end_time=EVENT["end_date"],
        )

        assert response.status_code == 201

    def test_unknown_event(self, db_client: FlaskClient, admin: ApiUser) -> None:
        response = _create_session(db_client, admin, 999_999)

        assert response.status_code == 404
        assert response.get_json() == {"message": "Event not found"}

    def test_unknown_speaker(
        self, db_client: FlaskClient, db_session: Session, organizer: ApiUser, event_id: int
    ) -> None:
        response = _create_session(db_client, organizer, event_id, speaker_id=999_999)

        assert response.status_code == 404
        assert response.get_json() == {"message": "Speaker not found"}
        assert db_session.scalar(select(func.count()).select_from(SessionModel)) == 0

    @pytest.mark.parametrize(
        ("start_time", "end_time"),
        [
            ("2030-05-10T09:30:00+00:00", "2030-05-10T11:00:00+00:00"),
            ("2030-05-10T17:30:00+00:00", "2030-05-10T19:00:00+00:00"),
            ("2030-05-11T10:00:00+00:00", "2030-05-11T11:00:00+00:00"),
        ],
        ids=["starts_before_event", "ends_after_event", "outside_event"],
    )
    def test_rejects_sessions_outside_the_event(
        self,
        db_client: FlaskClient,
        organizer: ApiUser,
        event_id: int,
        start_time: str,
        end_time: str,
    ) -> None:
        response = _create_session(
            db_client, organizer, event_id, start_time=start_time, end_time=end_time
        )

        assert response.status_code == 422
        assert response.get_json() == {
            "message": "Session must take place within the event schedule"
        }

    @pytest.mark.parametrize(
        ("overrides", "message"),
        [
            ({"capacity": 0}, "capacity must be greater than zero"),
            ({"capacity": -1}, "capacity must be greater than zero"),
            ({"title": "   "}, "title must not be blank"),
            ({"end_time": SESSION["start_time"]}, "Start must be before end"),
            ({"end_time": "2030-05-10T10:30:00+00:00"}, "Start must be before end"),
        ],
    )
    def test_rejects_business_rule_violations(
        self,
        db_client: FlaskClient,
        organizer: ApiUser,
        event_id: int,
        overrides: dict[str, Any],
        message: str,
    ) -> None:
        response = _create_session(db_client, organizer, event_id, **overrides)

        assert response.status_code == 422
        assert response.get_json() == {"message": message}

    @pytest.mark.parametrize(
        ("overrides", "field"),
        [
            ({"capacity": "10"}, "capacity"),
            ({"capacity": 2.5}, "capacity"),
            ({"capacity": None}, "capacity"),
            ({"capacity": 1_000_001}, "capacity"),
            ({"title": "x" * 201}, "title"),
            ({"start_time": "2030-05-10T11:00:00"}, "start_time"),
            ({"end_time": "tomorrow"}, "end_time"),
            ({"speaker_id": "1"}, "speaker_id"),
            ({"speaker_id": 0}, "speaker_id"),
            ({"speaker_id": 2_147_483_648}, "speaker_id"),
            ({"event_id": 1}, "event_id"),
            ({"created_by": 1}, "created_by"),
            ({"id": 1}, "id"),
        ],
    )
    def test_rejects_malformed_payload(
        self,
        db_client: FlaskClient,
        organizer: ApiUser,
        event_id: int,
        overrides: dict[str, Any],
        field: str,
    ) -> None:
        response = _create_session(db_client, organizer, event_id, **overrides)

        assert response.status_code == 422
        assert field in response.get_json()["errors"]["json"]

    def test_rejects_missing_required_fields(
        self, db_client: FlaskClient, organizer: ApiUser, event_id: int
    ) -> None:
        response = db_client.post(
            f"/api/events/{event_id}/sessions", json={}, headers=organizer.headers
        )

        assert response.status_code == 422
        assert set(response.get_json()["errors"]["json"]) == {
            "title",
            "start_time",
            "end_time",
            "capacity",
        }

    def test_organizer_cannot_add_sessions_to_foreign_event(
        self, db_client: FlaskClient, other_organizer: ApiUser, event_id: int
    ) -> None:
        response = _create_session(db_client, other_organizer, event_id)

        assert response.status_code == 403
        assert response.get_json() == {"message": "You can only manage your own events"}

    def test_attendee_is_forbidden(
        self, db_client: FlaskClient, attendee: ApiUser, event_id: int
    ) -> None:
        assert _create_session(db_client, attendee, event_id).status_code == 403

    def test_requires_authentication(self, db_client: FlaskClient, event_id: int) -> None:
        response = _create_session(db_client, None, event_id)

        assert response.status_code == 401
        assert response.get_json() == {"message": "Missing bearer token"}

    def test_rejects_invalid_token(self, db_client: FlaskClient, event_id: int) -> None:
        response = db_client.post(
            f"/api/events/{event_id}/sessions",
            json=SESSION,
            headers={"Authorization": "Bearer not-a-jwt"},
        )

        assert response.status_code == 401

    @pytest.mark.parametrize("status", ["CANCELLED", "COMPLETED"])
    def test_rejects_final_events(
        self, db_client: FlaskClient, organizer: ApiUser, status: str
    ) -> None:
        event_id = _create_event(db_client, organizer, publish=True)
        _set_event_status(db_client, organizer, event_id, status)

        response = _create_session(db_client, organizer, event_id)

        assert response.status_code == 409
        assert response.get_json() == {
            "message": "Cancelled or completed events cannot be modified"
        }


class TestReadSessions:
    def test_public_can_read_sessions_of_published_events(
        self, db_client: FlaskClient, organizer: ApiUser
    ) -> None:
        event_id = _create_event(db_client, organizer, publish=True)
        late = _create_session_id(
            db_client,
            organizer,
            event_id,
            title="Late",
            start_time="2030-05-10T15:00:00+00:00",
            end_time="2030-05-10T16:00:00+00:00",
        )
        early = _create_session_id(db_client, organizer, event_id, title="Early")

        listing = db_client.get(f"/api/events/{event_id}/sessions")
        detail = db_client.get(f"/api/sessions/{late}")

        assert listing.status_code == 200
        assert [item["id"] for item in listing.get_json()] == [early, late]
        assert detail.status_code == 200
        assert detail.get_json()["title"] == "Late"

    def test_event_without_sessions_returns_empty_list(
        self, db_client: FlaskClient, organizer: ApiUser
    ) -> None:
        event_id = _create_event(db_client, organizer, publish=True)

        response = db_client.get(f"/api/events/{event_id}/sessions")

        assert response.status_code == 200
        assert response.get_json() == []

    @pytest.mark.parametrize("viewer", [None, "attendee", "other_organizer"])
    def test_sessions_of_unpublished_events_are_hidden(
        self,
        db_client: FlaskClient,
        organizer: ApiUser,
        event_id: int,
        request: pytest.FixtureRequest,
        viewer: str | None,
    ) -> None:
        session_id = _create_session_id(db_client, organizer, event_id)
        headers = request.getfixturevalue(viewer).headers if viewer else {}

        listing = db_client.get(f"/api/events/{event_id}/sessions", headers=headers)
        detail = db_client.get(f"/api/sessions/{session_id}", headers=headers)

        assert listing.status_code == 404
        assert listing.get_json() == {"message": "Event not found"}
        assert detail.status_code == 404
        assert detail.get_json() == {"message": "Session not found"}

    @pytest.mark.parametrize("viewer", ["organizer", "admin"])
    def test_managers_read_sessions_of_unpublished_events(
        self,
        db_client: FlaskClient,
        organizer: ApiUser,
        event_id: int,
        request: pytest.FixtureRequest,
        viewer: str,
    ) -> None:
        session_id = _create_session_id(db_client, organizer, event_id)
        headers = request.getfixturevalue(viewer).headers

        assert db_client.get(f"/api/events/{event_id}/sessions", headers=headers).status_code == 200
        assert db_client.get(f"/api/sessions/{session_id}", headers=headers).status_code == 200

    def test_invalid_token_is_rejected_on_public_reads(self, db_client: FlaskClient) -> None:
        headers = {"Authorization": "Bearer bad"}

        assert db_client.get("/api/events/1/sessions", headers=headers).status_code == 401
        assert db_client.get("/api/sessions/1", headers=headers).status_code == 401

    @pytest.mark.parametrize("raw_id", ["999999", "abc", "-1", "0.5", "2147483648"])
    def test_unknown_or_invalid_ids_return_not_found(
        self, db_client: FlaskClient, raw_id: str
    ) -> None:
        for url in (f"/api/sessions/{raw_id}", f"/api/events/{raw_id}/sessions"):
            response = db_client.get(url)

            assert response.status_code == 404
            assert "message" in response.get_json()


class TestUpdateSession:
    @pytest.mark.parametrize("role", ["organizer", "admin"])
    def test_updates_session(
        self,
        db_client: FlaskClient,
        organizer: ApiUser,
        event_id: int,
        speaker_id: int,
        request: pytest.FixtureRequest,
        role: str,
    ) -> None:
        session_id = _create_session_id(db_client, organizer, event_id)

        response = _update_session(
            db_client,
            request.getfixturevalue(role),
            session_id,
            title="Advanced architecture",
            capacity=25,
            speaker_id=speaker_id,
        )
        body = response.get_json()

        assert response.status_code == 200
        assert (body["title"], body["capacity"], body["speaker_id"]) == (
            "Advanced architecture",
            25,
            speaker_id,
        )
        assert (body["id"], body["event_id"]) == (session_id, event_id)

    def test_omitting_speaker_removes_it(
        self, db_client: FlaskClient, organizer: ApiUser, event_id: int, speaker_id: int
    ) -> None:
        session_id = _create_session_id(db_client, organizer, event_id, speaker_id=speaker_id)

        response = _update_session(db_client, organizer, session_id)

        assert response.get_json()["speaker_id"] is None

    def test_organizer_cannot_update_foreign_session(
        self,
        db_client: FlaskClient,
        organizer: ApiUser,
        other_organizer: ApiUser,
        event_id: int,
    ) -> None:
        session_id = _create_session_id(db_client, organizer, event_id)

        response = _update_session(db_client, other_organizer, session_id, title="Hijacked")

        assert response.status_code == 403

    def test_attendee_cannot_update(
        self, db_client: FlaskClient, organizer: ApiUser, attendee: ApiUser, event_id: int
    ) -> None:
        session_id = _create_session_id(db_client, organizer, event_id)

        assert _update_session(db_client, attendee, session_id).status_code == 403

    def test_requires_authentication(self, db_client: FlaskClient) -> None:
        assert db_client.put("/api/sessions/1", json=SESSION).status_code == 401

    def test_unknown_session(self, db_client: FlaskClient, admin: ApiUser) -> None:
        response = _update_session(db_client, admin, 999_999)

        assert response.status_code == 404
        assert response.get_json() == {"message": "Session not found"}

    @pytest.mark.parametrize(
        ("overrides", "status_code"),
        [
            ({"capacity": 0}, 422),
            ({"end_time": "2030-05-10T19:00:00+00:00"}, 422),
            ({"speaker_id": 999_999}, 404),
            ({"event_id": 2}, 422),
        ],
    )
    def test_validates_changes(
        self,
        db_client: FlaskClient,
        organizer: ApiUser,
        event_id: int,
        overrides: dict[str, Any],
        status_code: int,
    ) -> None:
        session_id = _create_session_id(db_client, organizer, event_id)

        assert _update_session(db_client, organizer, session_id, **overrides).status_code == (
            status_code
        )

    def test_rejects_sessions_of_cancelled_events(
        self, db_client: FlaskClient, organizer: ApiUser, event_id: int
    ) -> None:
        session_id = _create_session_id(db_client, organizer, event_id)
        _set_event_status(db_client, organizer, event_id, "CANCELLED")

        assert _update_session(db_client, organizer, session_id).status_code == 409


class TestDeleteSession:
    @pytest.mark.parametrize("role", ["organizer", "admin"])
    def test_deletes_session(
        self,
        db_client: FlaskClient,
        organizer: ApiUser,
        event_id: int,
        request: pytest.FixtureRequest,
        role: str,
    ) -> None:
        session_id = _create_session_id(db_client, organizer, event_id)

        response = db_client.delete(
            f"/api/sessions/{session_id}", headers=request.getfixturevalue(role).headers
        )

        assert response.status_code == 204
        assert response.data == b""
        assert (
            db_client.get(f"/api/sessions/{session_id}", headers=organizer.headers).status_code
            == 404
        )

    def test_organizer_cannot_delete_foreign_session(
        self,
        db_client: FlaskClient,
        organizer: ApiUser,
        other_organizer: ApiUser,
        event_id: int,
    ) -> None:
        session_id = _create_session_id(db_client, organizer, event_id)

        response = db_client.delete(f"/api/sessions/{session_id}", headers=other_organizer.headers)

        assert response.status_code == 403
        assert (
            db_client.get(f"/api/sessions/{session_id}", headers=organizer.headers).status_code
            == 200
        )

    def test_attendee_cannot_delete(
        self, db_client: FlaskClient, organizer: ApiUser, attendee: ApiUser, event_id: int
    ) -> None:
        session_id = _create_session_id(db_client, organizer, event_id)

        response = db_client.delete(f"/api/sessions/{session_id}", headers=attendee.headers)

        assert response.status_code == 403

    def test_requires_authentication(self, db_client: FlaskClient) -> None:
        assert db_client.delete("/api/sessions/1").status_code == 401

    def test_unknown_session(self, db_client: FlaskClient, admin: ApiUser) -> None:
        assert db_client.delete("/api/sessions/999999", headers=admin.headers).status_code == 404

    def test_rejects_sessions_of_completed_events(
        self, db_client: FlaskClient, organizer: ApiUser
    ) -> None:
        event_id = _create_event(db_client, organizer, publish=True)
        session_id = _create_session_id(db_client, organizer, event_id)
        _set_event_status(db_client, organizer, event_id, "COMPLETED")

        response = db_client.delete(f"/api/sessions/{session_id}", headers=organizer.headers)

        assert response.status_code == 409

    def test_deleting_a_draft_event_removes_its_sessions(
        self, db_client: FlaskClient, db_session: Session, organizer: ApiUser, event_id: int
    ) -> None:
        _create_session_id(db_client, organizer, event_id)

        db_client.delete(f"/api/events/{event_id}", headers=organizer.headers)

        assert db_session.scalar(select(func.count()).select_from(SessionModel)) == 0
