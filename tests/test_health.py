"""Tests for the health endpoint and the placeholder home page."""


def test_health_returns_ok(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200

    data = response.get_json()
    assert data["status"] == "ok"
    assert data["app"] == "MySpott"
    assert data["environment"] == "testing"


def test_home_page_loads(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "MySpott" in response.get_data(as_text=True)


def test_unknown_url_returns_404(client):
    response = client.get("/this-page-does-not-exist")
    assert response.status_code == 404