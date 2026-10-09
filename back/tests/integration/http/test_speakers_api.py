import pytest
from flask.testing import FlaskClient
from sqlalchemy.orm import Session

from app.domain.entities import Speaker
from app.infrastructure.database.repositories import SqlAlchemySpeakerRepository
from tests.integration.http.conftest import ApiUser


@pytest.fixture
def seeded_speakers(db_session: Session) -> None:
    speakers = SqlAlchemySpeakerRepository(db_session)
    speakers.add(Speaker(name="Grace Hopper", bio="COBOL pioneer", email="grace@example.com"))
    speakers.add(Speaker(name="Ada Lovelace", email="ada@example.com"))
    speakers.add(Speaker(name="Barbara Liskov", bio=None))
    db_session.commit()


@pytest.mark.usefixtures("seeded_speakers")
class TestListSpeakers:
    def test_is_public_and_ordered_by_name(self, db_client: FlaskClient) -> None:
        response = db_client.get("/api/speakers")

        assert response.status_code == 200
        body = response.get_json()
        assert [item["name"] for item in body["items"]] == [
            "Ada Lovelace",
            "Barbara Liskov",
            "Grace Hopper",
        ]
        assert (body["total"], body["page"], body["per_page"], body["pages"]) == (3, 1, 10, 1)

    def test_exposes_only_public_fields(self, db_client: FlaskClient) -> None:
        items = db_client.get("/api/speakers").get_json()["items"]

        assert all(set(item) == {"id", "name", "bio"} for item in items)
        assert "grace@example.com" not in db_client.get("/api/speakers").get_data(as_text=True)

    def test_paginates(self, db_client: FlaskClient) -> None:
        body = db_client.get("/api/speakers?page=2&per_page=2").get_json()

        assert [item["name"] for item in body["items"]] == ["Grace Hopper"]
        assert (body["total"], body["page"], body["pages"]) == (3, 2, 2)

    def test_accepts_authenticated_users(self, db_client: FlaskClient, attendee: ApiUser) -> None:
        response = db_client.get("/api/speakers", headers=attendee.headers)

        assert response.status_code == 200

    def test_rejects_an_invalid_token(self, db_client: FlaskClient) -> None:
        response = db_client.get("/api/speakers", headers={"Authorization": "Bearer nope"})

        assert response.status_code == 401

    @pytest.mark.parametrize("query", ["per_page=101", "page=0", "per_page=abc"])
    def test_rejects_invalid_pagination(self, db_client: FlaskClient, query: str) -> None:
        response = db_client.get(f"/api/speakers?{query}")

        assert response.status_code == 422


def test_empty_catalog(db_client: FlaskClient) -> None:
    body = db_client.get("/api/speakers").get_json()

    assert body == {"items": [], "total": 0, "page": 1, "per_page": 10, "pages": 0}
