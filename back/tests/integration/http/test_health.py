from flask.testing import FlaskClient


def test_health_reports_ok_without_authentication(client: FlaskClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}
