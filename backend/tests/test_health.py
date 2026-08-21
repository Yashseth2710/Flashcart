from fastapi.testclient import TestClient


def test_health_reports_environment_and_database(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"ok", "degraded"}
    assert body["database"] in {"connected", "unreachable", "not_configured"}


def test_health_is_degraded_without_a_database(client: TestClient, monkeypatch) -> None:
    from app.api.v1 import health

    monkeypatch.setattr(health, "check_database", lambda: "not_configured")

    body = client.get("/api/v1/health").json()

    assert body["status"] == "degraded"
    assert body["database"] == "not_configured"
