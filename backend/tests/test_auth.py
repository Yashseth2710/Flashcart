"""Registering, signing in, and what each kind of account is allowed to do."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import create_access_token, hash_password
from app.models import User, UserRole
from tests.factories import make_user

GOOD_PASSWORD = "a-long-enough-password"


def register(client: TestClient, email: str = "new@example.com", password: str = GOOD_PASSWORD):
    return client.post(
        "/api/v1/auth/register",
        json={"name": "New Person", "email": email, "password": password},
    )


def test_registering_creates_a_customer_and_signs_them_in(client: TestClient) -> None:
    response = register(client)

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "new@example.com"
    assert body["role"] == "CUSTOMER"
    assert get_settings().cookie_name in response.cookies


def test_the_password_never_comes_back(client: TestClient) -> None:
    body = register(client).json()

    assert "password" not in body
    assert "password_hash" not in body


def test_the_stored_password_is_hashed(client: TestClient, db: Session) -> None:
    register(client, email="hashed@example.com")

    user = db.query(User).filter_by(email="hashed@example.com").one()
    assert user.password_hash != GOOD_PASSWORD
    assert user.password_hash.startswith("$argon2")


def test_an_email_can_only_be_registered_once(client: TestClient) -> None:
    register(client, email="taken@example.com")

    response = register(client, email="taken@example.com")

    assert response.status_code == 409


def test_email_case_and_spacing_do_not_create_a_second_account(client: TestClient) -> None:
    register(client, email="person@example.com")

    response = register(client, email="  PERSON@example.com  ")

    assert response.status_code == 409


@pytest.mark.parametrize("password", ["short", "1234567"])
def test_a_password_must_be_long_enough(client: TestClient, password: str) -> None:
    assert register(client, password=password).status_code == 422


def test_an_address_that_is_not_an_email_is_refused(client: TestClient) -> None:
    assert register(client, email="not-an-email").status_code == 422


def test_signing_in_returns_the_account(client: TestClient, db: Session) -> None:
    user = make_user(db)
    user.password_hash = hash_password(GOOD_PASSWORD)
    db.flush()

    response = client.post(
        "/api/v1/auth/login", json={"email": user.email, "password": GOOD_PASSWORD}
    )

    assert response.status_code == 200
    assert response.json()["email"] == user.email


def test_the_wrong_password_is_refused(client: TestClient, db: Session) -> None:
    user = make_user(db)
    user.password_hash = hash_password(GOOD_PASSWORD)
    db.flush()

    response = client.post(
        "/api/v1/auth/login", json={"email": user.email, "password": "not-the-password"}
    )

    assert response.status_code == 401


def test_an_unknown_address_gets_the_same_answer_as_a_wrong_password(client: TestClient) -> None:
    """Different wording here would tell an attacker which emails are registered."""
    response = client.post(
        "/api/v1/auth/login", json={"email": "nobody@example.com", "password": GOOD_PASSWORD}
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "That email and password do not match."


def test_the_session_cookie_is_not_readable_by_page_scripts(client: TestClient) -> None:
    response = register(client)

    cookie = response.headers["set-cookie"]
    assert "httponly" in cookie.lower()
    assert "samesite=lax" in cookie.lower()


def test_signing_out_clears_the_session(client: TestClient) -> None:
    register(client)

    client.post("/api/v1/auth/logout")

    assert client.get("/api/v1/auth/me").status_code == 401


def test_a_signed_in_person_can_read_their_own_profile(client: TestClient) -> None:
    register(client, email="reader@example.com")

    response = client.get("/api/v1/auth/me")

    assert response.status_code == 200
    assert response.json()["email"] == "reader@example.com"


def test_a_stranger_cannot_read_a_profile(client: TestClient) -> None:
    assert client.get("/api/v1/auth/me").status_code == 401


def test_a_made_up_token_is_refused(client: TestClient) -> None:
    client.cookies.set(get_settings().cookie_name, "not-a-real-token")

    assert client.get("/api/v1/auth/me").status_code == 401


def test_a_token_signed_with_another_key_is_refused(client: TestClient, db: Session) -> None:
    """A token FlashCart did not sign must not be accepted, however well-formed."""
    import jwt

    user = make_user(db)
    forged = jwt.encode({"sub": str(user.id), "role": "ADMIN"}, "not-our-secret", algorithm="HS256")
    client.cookies.set(get_settings().cookie_name, forged)

    assert client.get("/api/v1/auth/me").status_code == 401


def test_a_token_for_a_deleted_account_is_refused(client: TestClient, db: Session) -> None:
    """The account is re-read on every request rather than trusted from the token."""
    user = make_user(db)
    token = create_access_token(str(user.id), user.role.value)
    db.delete(user)
    db.flush()
    client.cookies.set(get_settings().cookie_name, token)

    assert client.get("/api/v1/auth/me").status_code == 401


def test_a_role_claimed_in_the_token_does_not_grant_it(client: TestClient, db: Session) -> None:
    """Authority comes from the stored account, not from what the token asserts."""
    user = make_user(db, role=UserRole.CUSTOMER)
    token = create_access_token(str(user.id), "ADMIN")
    client.cookies.set(get_settings().cookie_name, token)

    assert client.get("/api/v1/auth/me").json()["role"] == "CUSTOMER"
