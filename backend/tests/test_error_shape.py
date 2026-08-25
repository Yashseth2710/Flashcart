"""What every answer looks like when something goes wrong, and what it never says.

A client should not have to know which layer refused it, and someone probing
should not learn how the inside is built from an error message.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.headers import SAFE_HEADERS
from app.core.logging import REQUEST_ID_HEADER
from app.core.security import create_access_token, hash_password
from app.models import User
from tests.factories import make_user

PASSWORD = "a-long-enough-password"


@pytest.fixture
def breaking_client(db: Session):
    """A client that lets the app answer its own unhandled errors.

    By default the test client re-raises anything the server did not catch,
    which is useful for finding bugs but hides the very thing under test here:
    what a real caller is shown when something breaks unexpectedly.
    """
    from app.core.limits import counting_session
    from app.db.session import get_db
    from app.main import app
    from tests.conftest import survives_closing

    borrowed = survives_closing(db)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[counting_session] = lambda: borrowed
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def signed_in(client: TestClient, db: Session) -> User:
    user = make_user(db)
    user.password_hash = hash_password(PASSWORD)
    db.flush()
    from app.core.config import get_settings

    client.cookies.set(get_settings().cookie_name, create_access_token(str(user.id), "CUSTOMER"))
    return user


# One shape


def test_a_refusal_carries_the_message_and_the_status(client: TestClient) -> None:
    body = client.get("/api/v1/holds").json()

    assert body["detail"] == "Sign in to continue."
    assert body["status"] == 401


def test_a_refusal_carries_the_id_it_was_logged_under(client: TestClient) -> None:
    """Which is what turns "it broke" into a line somebody can look up."""
    response = client.get("/api/v1/holds")

    assert response.json()["request_id"]
    assert response.headers[REQUEST_ID_HEADER] == response.json()["request_id"]


def test_a_missing_route_answers_in_the_same_shape(client: TestClient) -> None:
    """Even the ones the router raises rather than the application."""
    body = client.get("/api/v1/nothing-here").json()

    assert body["status"] == 404
    assert isinstance(body["detail"], str)


def test_a_malformed_body_names_the_field(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/login", json={"email": "not-an-email", "password": "short"}
    )

    body = response.json()
    assert response.status_code == 422
    assert [field["field"] for field in body["fields"]] == ["email"]


def test_a_malformed_body_never_echoes_what_was_sent(client: TestClient) -> None:
    """A validation error that quotes the value back would put a password in
    the logs of anything that records responses."""
    secret = "a-password-nobody-should-see"

    response = client.post("/api/v1/auth/login", json={"email": "no", "password": secret})

    assert secret not in response.text


def test_a_missing_field_is_named_rather_than_guessed(client: TestClient) -> None:
    response = client.post("/api/v1/auth/login", json={"email": "someone@example.com"})

    fields = [field["field"] for field in response.json()["fields"]]
    assert "password" in fields


# What is never said


def test_an_unexpected_failure_says_nothing_about_the_inside(
    breaking_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The cause goes to the logs in full and to the client not at all."""
    from app.api.v1 import health

    def explode() -> str:
        raise RuntimeError("connection to db-primary-7 at 10.0.0.4 refused")

    monkeypatch.setattr(health, "check_database", explode)

    response = breaking_client.get("/api/v1/health")
    body = response.text

    assert response.status_code == 500
    assert "10.0.0.4" not in body
    assert "db-primary-7" not in body
    assert "Traceback" not in body
    assert "RuntimeError" not in body


def test_an_unexpected_failure_still_hands_back_an_id(
    breaking_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.api.v1 import health

    def explode() -> str:
        raise RuntimeError("something private")

    monkeypatch.setattr(health, "check_database", explode)

    body = breaking_client.get("/api/v1/health").json()

    assert body["request_id"]
    assert "orders" in body["detail"]


# Headers


@pytest.mark.parametrize("header", sorted(SAFE_HEADERS))
def test_every_answer_carries_the_safe_headers(client: TestClient, header: str) -> None:
    response = client.get("/api/v1/health")

    assert response.headers[header] == SAFE_HEADERS[header]


def test_a_request_id_supplied_by_the_caller_is_kept(client: TestClient) -> None:
    """So a trace that starts in the browser stays one trace across the boundary."""
    response = client.get("/api/v1/health", headers={REQUEST_ID_HEADER: "trace-from-the-browser"})

    assert response.headers[REQUEST_ID_HEADER] == "trace-from-the-browser"


def test_every_request_gets_an_id_of_its_own(client: TestClient) -> None:
    first = client.get("/api/v1/health").headers[REQUEST_ID_HEADER]
    second = client.get("/api/v1/health").headers[REQUEST_ID_HEADER]

    assert first and second and first != second
