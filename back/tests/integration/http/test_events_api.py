from datetime import timedelta

import pytest
from flask.testing import FlaskClient
from sqlalchemy.orm import Session

from app.domain.enums import EventStatus
from app.infrastructure.database.repositories import (
    SqlAlchemyEventRepository,
    SqlAlchemyUserRepository,
)
from tests.factories import EVENT_START, build_event, build_user


@pytest.fixture
def seeded_events(db_session: Session) -> None:
    creator = SqlAlchemyUserRepository(db_session).add(build_user())
    events = SqlAlchemyEventRepository(db_session)
    for index, name in enumerate(["Python Day", "Django Summit", "Rust Meetup", "Python Night"]):
        events.add(
            build_event(
                name=name,
                description=None,
                location="Bogota",
                created_by=creator.id,
                start_date=EVENT_START + timedelta(days=index),
                end_date=EVENT_START + timedelta(days=index, hours=4),
            )
        )
    events.add(build_event(name="Python Draft", created_by=creator.id, status=EventStatus.DRAFT))
    db_session.commit()


@pytest.mark.usefixtures("seeded_events")
class TestListEvents:
    def test_lists_only_published_events_ordered_by_start_date(
        self, db_client: FlaskClient
    ) -> None:
        body = db_client.get("/api/events").get_json()

        assert [event["name"] for event in body["items"]] == [
            "Python Day",
            "Django Summit",
            "Rust Meetup",
            "Python Night",
        ]
        assert {event["status"] for event in body["items"]} == {"PUBLISHED"}
        assert (body["total"], body["page"], body["per_page"], body["pages"]) == (4, 1, 10, 1)

    def test_filters_by_search_term(self, db_client: FlaskClient) -> None:
        body = db_client.get("/api/events?search=python").get_json()

        assert [event["name"] for event in body["items"]] == ["Python Day", "Python Night"]

    def test_paginates_results(self, db_client: FlaskClient) -> None:
        body = db_client.get("/api/events?page=2&per_page=3").get_json()

        assert [event["name"] for event in body["items"]] == ["Python Night"]
        assert (body["total"], body["page"], body["per_page"], body["pages"]) == (4, 2, 3, 2)

    @pytest.mark.parametrize("search", ["python", "Python", "PYTHON", "pyTHon"])
    def test_search_is_case_insensitive(self, db_client: FlaskClient, search: str) -> None:
        body = db_client.get(f"/api/events?search={search}").get_json()

        assert [event["name"] for event in body["items"]] == ["Python Day", "Python Night"]

    def test_search_does_not_expose_drafts(self, db_client: FlaskClient) -> None:
        body = db_client.get("/api/events?search=draft").get_json()

        assert body["items"] == []

    def test_search_combined_with_pagination(self, db_client: FlaskClient) -> None:
        body = db_client.get("/api/events?search=python&page=2&per_page=1").get_json()

        assert [event["name"] for event in body["items"]] == ["Python Night"]
        assert (body["total"], body["pages"]) == (2, 2)

    @pytest.mark.parametrize(
        "payload",
        [
            "' OR '1'='1",
            "%' OR 1=1 --",
            "'; DROP TABLE events; --",
            "%",
            "_",
            "\\",
        ],
    )
    def test_sql_injection_attempts_are_treated_as_literal_text(
        self, db_client: FlaskClient, payload: str
    ) -> None:
        response = db_client.get("/api/events", query_string={"search": payload})

        assert response.status_code == 200
        assert response.get_json()["total"] == 0
        assert db_client.get("/api/events").get_json()["total"] == 4

    def test_page_beyond_last_returns_empty_items(self, db_client: FlaskClient) -> None:
        body = db_client.get("/api/events?page=50").get_json()

        assert body["items"] == []
        assert body["total"] == 4

    @pytest.mark.parametrize(
        "query",
        [
            "page=0",
            "page=-1",
            "page=100001",
            "page=99999999999999999999999",
            "per_page=0",
            "per_page=101",
            "per_page=1000000",
            "per_page=abc",
            f"search={'x' * 101}",
        ],
    )
    def test_rejects_invalid_pagination(self, db_client: FlaskClient, query: str) -> None:
        response = db_client.get(f"/api/events?{query}")

        assert response.status_code == 422
        assert "query" in response.get_json()["errors"]
