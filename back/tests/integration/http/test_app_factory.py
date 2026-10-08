from flask import Flask
from flask.testing import FlaskClient

from app.bootstrap import create_app
from app.container import Container
from app.infrastructure.config import Settings


def test_creates_independent_apps_wired_with_the_given_settings(settings: Settings) -> None:
    first, second = create_app(settings), create_app(settings)

    assert first is not second
    assert first.testing
    assert isinstance(first.extensions["container"], Container)
    assert first.extensions["container"].settings is settings


def test_openapi_spec_documents_routes_and_bearer_security(client: FlaskClient) -> None:
    response = client.get("/openapi.json")
    spec = response.get_json()

    assert response.status_code == 200
    assert spec["info"]["title"] == "Mis Eventos API"
    assert spec["components"]["securitySchemes"]["bearerAuth"] == {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
    }
    assert {
        "/health",
        "/api/auth/register",
        "/api/auth/login",
        "/api/auth/me",
        "/api/events",
    } <= set(spec["paths"])
    assert spec["paths"]["/api/auth/me"]["get"]["security"] == [{"bearerAuth": []}]
    assert "security" not in spec["paths"]["/health"]["get"]
    assert {"page", "per_page", "search"} <= {
        parameter["name"] for parameter in spec["paths"]["/api/events"]["get"]["parameters"]
    }


def test_openapi_spec_documents_event_management(client: FlaskClient) -> None:
    paths = client.get("/openapi.json").get_json()["paths"]
    collection, item = paths["/api/events"], paths["/api/events/{event_id}"]

    assert collection["post"]["security"] == [{"bearerAuth": []}]
    assert collection["get"]["security"] == [{}, {"bearerAuth": []}]
    assert {"201", "401", "403", "422"} <= set(collection["post"]["responses"])
    assert item["parameters"][0]["name"] == "event_id"
    assert {"200", "401", "403", "404", "409", "422"} <= set(item["put"]["responses"])
    assert {"200", "204", "401", "403", "404", "409"} <= set(item["delete"]["responses"])
    assert {"200", "404"} <= set(item["get"]["responses"])


def test_openapi_spec_documents_session_management(client: FlaskClient) -> None:
    paths = client.get("/openapi.json").get_json()["paths"]
    collection = paths["/api/events/{event_id}/sessions"]
    item = paths["/api/sessions/{session_id}"]

    assert collection["post"]["security"] == [{"bearerAuth": []}]
    assert collection["get"]["security"] == [{}, {"bearerAuth": []}]
    assert {"201", "401", "403", "404", "409", "422"} <= set(collection["post"]["responses"])
    assert {"200", "404"} <= set(collection["get"]["responses"])
    assert item["get"]["security"] == [{}, {"bearerAuth": []}]
    assert {"200", "401", "403", "404", "409", "422"} <= set(item["put"]["responses"])
    assert {"204", "401", "403", "404", "409"} <= set(item["delete"]["responses"])


def test_openapi_spec_documents_event_registrations(client: FlaskClient) -> None:
    paths = client.get("/openapi.json").get_json()["paths"]
    register = paths["/api/events/{event_id}/registrations"]["post"]
    mine = paths["/api/me/registrations"]["get"]

    assert register["security"] == [{"bearerAuth": []}]
    assert {"201", "401", "404", "409", "422"} <= set(register["responses"])
    assert mine["security"] == [{"bearerAuth": []}]
    assert {"200", "401"} <= set(mine["responses"])
    assert "parameters" not in mine


def test_swagger_ui_is_served(client: FlaskClient) -> None:
    response = client.get("/docs")

    assert response.status_code == 200
    assert b"swagger-ui" in response.data


def test_unknown_route_returns_json_error(client: FlaskClient) -> None:
    response = client.get("/does-not-exist")

    assert response.status_code == 404
    assert set(response.get_json()) == {"message"}


def test_wrong_method_returns_json_error(client: FlaskClient) -> None:
    response = client.delete("/health")

    assert response.status_code == 405
    assert "message" in response.get_json()


def test_unexpected_errors_hide_internal_details(app: Flask) -> None:
    @app.get("/boom")
    def boom() -> None:
        raise RuntimeError("database password is hunter2")

    response = app.test_client().get("/boom")

    assert response.status_code == 500
    assert response.get_json() == {"message": "Internal server error"}


def test_cors_allows_only_configured_origins(client: FlaskClient) -> None:
    allowed = client.get("/api/auth/me", headers={"Origin": "http://localhost:4200"})
    denied = client.get("/api/auth/me", headers={"Origin": "http://evil.example"})

    assert allowed.headers.get("Access-Control-Allow-Origin") == "http://localhost:4200"
    assert "Access-Control-Allow-Origin" not in denied.headers
