"""Event cover images through the API and PostgreSQL, with a fake image service (no network)."""

from typing import Any

import pytest
from flask import Flask
from flask.testing import FlaskClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.container import Container
from app.infrastructure.database.models import EventImageModel
from tests.integration.http.conftest import ApiUser
from tests.unit.application.fakes import FakeImageStorage

EVENT = {
    "name": "Python Conference",
    "description": None,
    "location": "Bucaramanga",
    "start_date": "2030-10-10T08:00:00-05:00",
    "end_date": "2030-10-10T18:00:00-05:00",
    "capacity": 150,
}
FILE = {"filename": "cover.jpg", "content_type": "image/jpeg", "size": 250_000}


@pytest.fixture
def storage(db_app: Flask) -> FakeImageStorage:
    fake = FakeImageStorage()
    container: Container = db_app.extensions["container"]
    container.image_storage = fake
    return fake


@pytest.fixture
def event_id(db_client: FlaskClient, organizer: ApiUser) -> int:
    response = db_client.post("/api/events", json=EVENT, headers=organizer.headers)
    assert response.status_code == 201, response.get_json()
    created: int = response.get_json()["id"]
    return created


def _authorize(client: FlaskClient, user: ApiUser, event_id: int, **file: Any) -> Any:
    return client.post(
        f"/api/events/{event_id}/images/upload", json={**FILE, **file}, headers=user.headers
    )


def _confirm(client: FlaskClient, user: ApiUser, event_id: int, public_id: str) -> Any:
    return client.post(
        f"/api/events/{event_id}/images/confirm",
        json={"public_id": public_id},
        headers=user.headers,
    )


def _upload(client: FlaskClient, user: ApiUser, event_id: int, storage: FakeImageStorage) -> str:
    """Authorization, then the direct upload the browser would make."""
    response = _authorize(client, user, event_id)
    assert response.status_code == 200, response.get_json()
    public_id: str = response.get_json()["public_id"]
    storage.upload(public_id)
    return public_id


def _stored_images(db_session: Session) -> list[EventImageModel]:
    return list(
        db_session.scalars(select(EventImageModel).execution_options(populate_existing=True))
    )


@pytest.mark.usefixtures("storage")
def test_existing_events_have_no_image(
    db_client: FlaskClient, organizer: ApiUser, event_id: int
) -> None:
    response = db_client.get(f"/api/events/{event_id}", headers=organizer.headers)

    assert response.get_json()["image"] is None


def test_authorization_returns_only_public_upload_parameters(
    db_client: FlaskClient, organizer: ApiUser, event_id: int, storage: FakeImageStorage
) -> None:
    response = _authorize(db_client, organizer, event_id)

    assert response.status_code == 200
    body = response.get_json()
    assert set(body) == {
        "upload_url",
        "cloud_name",
        "api_key",
        "timestamp",
        "signature",
        "public_id",
        "allowed_formats",
    }
    assert body["public_id"].startswith(f"mis-eventos/events/{event_id}/")
    assert "secret" not in str(body).lower()


def test_full_flow_stores_the_verified_metadata(
    db_client: FlaskClient,
    organizer: ApiUser,
    event_id: int,
    storage: FakeImageStorage,
    db_session: Session,
) -> None:
    public_id = _upload(db_client, organizer, event_id, storage)

    response = _confirm(db_client, organizer, event_id, public_id)

    assert response.status_code == 201, response.get_json()
    stored = storage.images[public_id]
    assert response.get_json() == {
        "public_id": public_id,
        "secure_url": stored.secure_url,
        "width": stored.width,
        "height": stored.height,
        "format": stored.format,
    }
    [row] = _stored_images(db_session)
    assert (row.event_id, row.public_id, row.bytes) == (event_id, public_id, stored.bytes)

    event = db_client.get(f"/api/events/{event_id}", headers=organizer.headers).get_json()
    assert event["image"]["public_id"] == public_id
    listed = db_client.get("/api/events", headers=organizer.headers).get_json()["items"]
    assert next(item for item in listed if item["id"] == event_id)["image"] is not None


def test_replacing_keeps_one_row_and_deletes_the_previous_file(
    db_client: FlaskClient,
    organizer: ApiUser,
    event_id: int,
    storage: FakeImageStorage,
    db_session: Session,
) -> None:
    old = _upload(db_client, organizer, event_id, storage)
    _confirm(db_client, organizer, event_id, old)
    new = _upload(db_client, organizer, event_id, storage)

    response = _confirm(db_client, organizer, event_id, new)

    assert response.status_code == 201
    assert [row.public_id for row in _stored_images(db_session)] == [new]
    assert storage.deleted == [old]


def test_confirming_twice_does_not_duplicate_the_image(
    db_client: FlaskClient,
    organizer: ApiUser,
    event_id: int,
    storage: FakeImageStorage,
    db_session: Session,
) -> None:
    public_id = _upload(db_client, organizer, event_id, storage)

    assert _confirm(db_client, organizer, event_id, public_id).status_code == 201
    assert _confirm(db_client, organizer, event_id, public_id).status_code == 201
    assert len(_stored_images(db_session)) == 1


def test_rejects_images_that_were_never_uploaded(
    db_client: FlaskClient, organizer: ApiUser, event_id: int, storage: FakeImageStorage
) -> None:
    public_id = _authorize(db_client, organizer, event_id).get_json()["public_id"]

    response = _confirm(db_client, organizer, event_id, public_id)

    assert response.status_code == 422
    assert response.get_json()["message"] == "The uploaded image could not be verified"


def test_rejects_images_of_another_event(
    db_client: FlaskClient, organizer: ApiUser, event_id: int, storage: FakeImageStorage
) -> None:
    other_id = db_client.post("/api/events", json=EVENT, headers=organizer.headers).get_json()["id"]
    public_id = _upload(db_client, organizer, other_id, storage)

    response = _confirm(db_client, organizer, event_id, public_id)

    assert response.status_code == 422


@pytest.mark.parametrize(
    ("file", "field"),
    [
        ({"content_type": "image/gif"}, None),
        ({"size": 5 * 1024 * 1024 + 1}, None),
        ({"size": 0}, "size"),
        ({"filename": ""}, "filename"),
        ({"signature": "forged"}, "signature"),
    ],
)
def test_rejects_invalid_upload_requests(
    db_client: FlaskClient,
    organizer: ApiUser,
    event_id: int,
    storage: FakeImageStorage,
    file: dict[str, Any],
    field: str | None,
) -> None:
    response = _authorize(db_client, organizer, event_id, **file)

    assert response.status_code == 422
    if field:
        assert field in str(response.get_json())
    assert storage.signed == []


@pytest.mark.parametrize("user", ["other_organizer", "attendee"])
def test_users_who_cannot_manage_the_event_are_forbidden(
    db_client: FlaskClient,
    organizer: ApiUser,
    event_id: int,
    storage: FakeImageStorage,
    db_session: Session,
    user: str,
    request: pytest.FixtureRequest,
) -> None:
    intruder: ApiUser = request.getfixturevalue(user)
    public_id = _upload(db_client, organizer, event_id, storage)

    assert _authorize(db_client, intruder, event_id).status_code == 403
    assert _confirm(db_client, intruder, event_id, public_id).status_code == 403
    _confirm(db_client, organizer, event_id, public_id)
    delete = db_client.delete(f"/api/events/{event_id}/images", headers=intruder.headers)
    assert delete.status_code == 403
    assert len(_stored_images(db_session)) == 1
    assert storage.deleted == []


@pytest.mark.usefixtures("storage")
def test_anonymous_users_must_authenticate(db_client: FlaskClient, event_id: int) -> None:
    assert db_client.post(f"/api/events/{event_id}/images/upload", json=FILE).status_code == 401
    confirm = db_client.post(f"/api/events/{event_id}/images/confirm", json={"public_id": "x"})
    assert confirm.status_code == 401
    assert db_client.delete(f"/api/events/{event_id}/images").status_code == 401


def test_admins_can_manage_images_of_any_event(
    db_client: FlaskClient,
    admin: ApiUser,
    event_id: int,
    storage: FakeImageStorage,
) -> None:
    public_id = _upload(db_client, admin, event_id, storage)

    assert _confirm(db_client, admin, event_id, public_id).status_code == 201


def test_removing_the_cover(
    db_client: FlaskClient,
    organizer: ApiUser,
    event_id: int,
    storage: FakeImageStorage,
    db_session: Session,
) -> None:
    public_id = _upload(db_client, organizer, event_id, storage)
    _confirm(db_client, organizer, event_id, public_id)

    response = db_client.delete(f"/api/events/{event_id}/images", headers=organizer.headers)

    assert response.status_code == 204
    assert _stored_images(db_session) == []
    assert storage.deleted == [public_id]
    again = db_client.delete(f"/api/events/{event_id}/images", headers=organizer.headers)
    assert again.status_code == 404


def test_deleting_a_draft_removes_its_image_row_and_file(
    db_client: FlaskClient,
    organizer: ApiUser,
    event_id: int,
    storage: FakeImageStorage,
    db_session: Session,
) -> None:
    public_id = _upload(db_client, organizer, event_id, storage)
    _confirm(db_client, organizer, event_id, public_id)

    response = db_client.delete(f"/api/events/{event_id}", headers=organizer.headers)

    assert response.status_code == 204
    assert db_session.scalar(select(func.count()).select_from(EventImageModel)) == 0
    assert storage.deleted == [public_id]


def test_an_image_service_failure_answers_502_without_details(
    db_client: FlaskClient, organizer: ApiUser, event_id: int, storage: FakeImageStorage
) -> None:
    public_id = _upload(db_client, organizer, event_id, storage)
    storage.fail_get = True

    response = _confirm(db_client, organizer, event_id, public_id)

    assert response.status_code == 502
    assert response.get_json() == {"message": "The image service could not complete the operation"}


def test_answers_503_when_cloudinary_is_not_configured(
    db_client: FlaskClient, organizer: ApiUser, event_id: int
) -> None:
    response = _authorize(db_client, organizer, event_id)

    assert response.status_code == 503
    assert response.get_json() == {"message": "Image uploads are not configured"}
