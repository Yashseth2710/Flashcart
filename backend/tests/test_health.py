from fastapi.testclient import TestClient

from app.api.v1 import health


def test_health_reports_a_connected_database(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(health, "check_database", lambda: "connected")

    body = client.get("/api/v1/health").json()

    assert body["status"] == "ok"
    assert body["database"] == "connected"


def test_health_is_degraded_without_a_database(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(health, "check_database", lambda: "not_configured")

    body = client.get("/api/v1/health").json()

    assert body["status"] == "degraded"
    assert body["database"] == "not_configured"


def test_health_is_degraded_when_the_database_refuses(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(health, "check_database", lambda: "unreachable")

    assert client.get("/api/v1/health").json()["status"] == "degraded"
