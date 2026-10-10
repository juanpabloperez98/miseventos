from datetime import UTC, datetime
from typing import Any

import pytest
from flask.testing import FlaskClient
from sqlalchemy import Connection, select, text
from sqlalchemy.orm import Session

from app.infrastructure.database.models import EventModel, SessionModel
from tests.integration.http.conftest import ApiUser

EVENT = {
    "name": "Python Conference",
    "description": None,
    "location": "Bucaramanga",
    "start_date": "2030-10-10T08:00:00-05:00",
    "end_date": "2030-10-10T23:59:00-05:00",
    "capacity": 150,
}
SESSION = {
    "title": "Clean architecture",
    "description": None,
    "start_time": "2030-10-10T14:30:00-05:00",
    "end_time": "2030-10-10T23:30:00-05:00",
    "capacity": 40,
}


def _create_event(client: FlaskClient, user: ApiUser, **overrides: Any) -> Any:
    return client.post("/api/events", json={**EVENT, **overrides}, headers=user.headers)


def _create_session(client: FlaskClient, user: ApiUser, event_id: int, **overrides: Any) -> Any:
    return client.post(
        f"/api/events/{event_id}/sessions", json={**SESSION, **overrides}, headers=user.headers
    )


@pytest.fixture
def event(db_client: FlaskClient, organizer: ApiUser) -> dict[str, Any]:
    response = _create_event(db_client, organizer)
    assert response.status_code == 201, response.get_json()
    body: dict[str, Any] = response.get_json()
    return body


def test_event_schedule_is_stored_as_instant_and_returned_in_utc(
    event: dict[str, Any], db_session: Session
) -> None:
    assert event["start_date"] == "2030-10-10T13:00:00+00:00"
    assert event["end_date"] == "2030-10-11T04:59:00+00:00"
    assert event["description"] is None

    stored = db_session.scalars(select(EventModel).where(EventModel.id == event["id"])).one()
    assert stored.start_date == datetime(2030, 10, 10, 13, 0, tzinfo=UTC)
    assert stored.end_date == datetime(2030, 10, 11, 4, 59, tzinfo=UTC)


def test_session_schedule_close_to_midnight_keeps_its_instant(
    db_client: FlaskClient, organizer: ApiUser, event: dict[str, Any], db_session: Session
) -> None:
    response = _create_session(db_client, organizer, event["id"])

    assert response.status_code == 201, response.get_json()
    body = response.get_json()
    assert body["start_time"] == "2030-10-10T19:30:00+00:00"
    assert body["end_time"] == "2030-10-11T04:30:00+00:00"
    assert body["speaker_id"] is None
    assert body["description"] is None

    stored = db_session.scalars(select(SessionModel).where(SessionModel.id == body["id"])).one()
    assert stored.start_time == datetime(2030, 10, 10, 19, 30, tzinfo=UTC)
    assert stored.end_time == datetime(2030, 10, 11, 4, 30, tzinfo=UTC)


def test_any_offset_of_the_same_instant_is_stored_identically(
    db_client: FlaskClient, organizer: ApiUser, event: dict[str, Any]
) -> None:
    colombia = _create_session(db_client, organizer, event["id"]).get_json()
    utc = _create_session(
        db_client,
        organizer,
        event["id"],
        start_time="2030-10-10T19:30:00Z",
        end_time="2030-10-11T04:30:00+00:00",
    ).get_json()

    assert (utc["start_time"], utc["end_time"]) == (colombia["start_time"], colombia["end_time"])


def test_answers_in_utc_whatever_the_timezone_of_the_database_session(
    db_client: FlaskClient, organizer: ApiUser, event: dict[str, Any], connection: Connection
) -> None:
    session_id = _create_session(db_client, organizer, event["id"]).get_json()["id"]

    connection.execute(text("SET LOCAL TIME ZONE 'America/Bogota'"))
    shown = connection.execute(
        text("SELECT start_time::text FROM sessions WHERE id = :id"), {"id": session_id}
    ).scalar_one()
    assert shown == "2030-10-10 14:30:00-05"

    response = db_client.get(f"/api/sessions/{session_id}", headers=organizer.headers)
    body = response.get_json()
    assert body["start_time"] == "2030-10-10T19:30:00+00:00"
    assert body["end_time"] == "2030-10-11T04:30:00+00:00"
    assert body["created_at"].endswith("+00:00")
    assert body["updated_at"].endswith("+00:00")


def test_saving_the_returned_schedule_again_does_not_shift_it(
    db_client: FlaskClient, organizer: ApiUser, event: dict[str, Any]
) -> None:
    created = _create_session(db_client, organizer, event["id"]).get_json()

    for _ in range(2):
        response = db_client.put(
            f"/api/sessions/{created['id']}",
            json={
                **SESSION,
                "start_time": created["start_time"],
                "end_time": created["end_time"],
            },
            headers=organizer.headers,
        )
        assert response.status_code == 200, response.get_json()
        created = response.get_json()

    assert created["start_time"] == "2030-10-10T19:30:00+00:00"
    assert created["end_time"] == "2030-10-11T04:30:00+00:00"


def test_session_must_still_be_inside_the_event_schedule(
    db_client: FlaskClient, organizer: ApiUser, event: dict[str, Any]
) -> None:
    response = _create_session(
        db_client, organizer, event["id"], end_time="2030-10-11T00:30:00-05:00"
    )

    assert response.status_code == 422, response.get_json()


def test_session_end_must_be_after_its_start(
    db_client: FlaskClient, organizer: ApiUser, event: dict[str, Any]
) -> None:
    response = _create_session(
        db_client,
        organizer,
        event["id"],
        start_time="2030-10-10T15:00:00-05:00",
        end_time="2030-10-10T14:00:00-05:00",
    )

    assert response.status_code == 422, response.get_json()


@pytest.mark.parametrize("field", ["start_time", "end_time"])
def test_session_dates_without_timezone_are_rejected(
    db_client: FlaskClient, organizer: ApiUser, event: dict[str, Any], field: str
) -> None:
    response = _create_session(db_client, organizer, event["id"], **{field: "2030-10-10T15:00:00"})

    assert response.status_code == 422
    assert field in str(response.get_json())


@pytest.mark.parametrize("field", ["start_date", "end_date"])
def test_event_dates_without_timezone_are_rejected(
    db_client: FlaskClient, organizer: ApiUser, field: str
) -> None:
    response = _create_event(db_client, organizer, **{field: "2030-10-10T15:00:00"})

    assert response.status_code == 422
    assert field in str(response.get_json())
