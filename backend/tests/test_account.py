"""Managing your own account: your details, your password, and closing it."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import create_access_token, hash_password, verify_password
from app.models import Order, Reservation, User
from tests.factories import make_sale_product, make_user

PASSWORD = "a-long-enough-password"


def signed_in(client: TestClient, db: Session) -> User:
    user = make_user(db)
    user.password_hash = hash_password(PASSWORD)
    db.flush()
    client.cookies.set(get_settings().cookie_name, create_access_token(str(user.id), "CUSTOMER"))
    return user


def test_the_account_page_shows_who_you_are(client: TestClient, db: Session) -> None:
    user = signed_in(client, db)

    body = client.get("/api/v1/auth/me").json()

    assert body["email"] == user.email
    assert body["role"] == "CUSTOMER"
    assert "password_hash" not in body


def test_you_can_change_your_name(client: TestClient, db: Session) -> None:
    signed_in(client, db)

    body = client.patch("/api/v1/auth/me", json={"name": "Ada Lovelace"}).json()

    assert body["name"] == "Ada Lovelace"


def test_a_blank_name_is_refused(client: TestClient, db: Session) -> None:
    signed_in(client, db)

    assert client.patch("/api/v1/auth/me", json={"name": "   "}).status_code == 422


def test_a_stranger_cannot_change_a_name(client: TestClient) -> None:
    assert client.patch("/api/v1/auth/me", json={"name": "Nobody"}).status_code == 401


def test_changing_your_password(client: TestClient, db: Session) -> None:
    user = signed_in(client, db)

    response = client.post(
        "/api/v1/auth/me/password",
        json={"current_password": PASSWORD, "new_password": "a-brand-new-password"},
    )

    assert response.status_code == 204
    db.refresh(user)
    assert verify_password("a-brand-new-password", user.password_hash)


def test_the_current_password_has_to_be_right(client: TestClient, db: Session) -> None:
    """Otherwise anyone borrowing an open browser could lock the owner out."""
    user = signed_in(client, db)

    response = client.post(
        "/api/v1/auth/me/password",
        json={"current_password": "not-the-password", "new_password": "a-brand-new-password"},
    )

    assert response.status_code == 401
    db.refresh(user)
    assert verify_password(PASSWORD, user.password_hash)


def test_a_short_new_password_is_refused(client: TestClient, db: Session) -> None:
    signed_in(client, db)

    response = client.post(
        "/api/v1/auth/me/password",
        json={"current_password": PASSWORD, "new_password": "short"},
    )

    assert response.status_code == 422


def test_closing_an_account_removes_it(client: TestClient, db: Session) -> None:
    user = signed_in(client, db)
    user_id = user.id

    response = client.post("/api/v1/auth/me/delete", json={"email": user.email})

    assert response.status_code == 204
    assert db.get(User, user_id) is None


def test_closing_an_account_signs_you_out(client: TestClient, db: Session) -> None:
    user = signed_in(client, db)

    response = client.post("/api/v1/auth/me/delete", json={"email": user.email})

    assert "max-age=0" in response.headers["set-cookie"].lower()


def test_the_email_has_to_be_typed_back_correctly(client: TestClient, db: Session) -> None:
    """A mistyped confirmation is a mistake, and deleting is not undoable."""
    user = signed_in(client, db)
    user_id = user.id

    response = client.post("/api/v1/auth/me/delete", json={"email": "someone@example.com"})

    assert response.status_code == 400
    assert db.get(User, user_id) is not None


def test_case_and_spacing_in_the_confirmation_are_forgiven(client: TestClient, db: Session) -> None:
    user = signed_in(client, db)

    response = client.post("/api/v1/auth/me/delete", json={"email": f"  {user.email.upper()}  "})

    assert response.status_code == 204


def test_an_account_with_an_order_is_kept(client: TestClient, db: Session) -> None:
    """Orders are a record of money changing hands, so the account stays."""
    user = signed_in(client, db)
    db.add(Order(user_id=user.id, subtotal=Decimal("49.99"), total=Decimal("49.99")))
    db.flush()

    response = client.post("/api/v1/auth/me/delete", json={"email": user.email})

    assert response.status_code == 409
    assert "contact support" in response.json()["detail"].lower()
    assert db.get(User, user.id) is not None


def test_closing_an_account_hands_its_holds_back(client: TestClient, db: Session) -> None:
    """Otherwise that stock would sit unavailable until the hold expired."""
    user = signed_in(client, db)
    sale_product = make_sale_product(db, allocated=10, max_per_user=2)
    sale_product.reserved_quantity = 2
    db.add(
        Reservation(
            user_id=user.id,
            flash_sale_product_id=sale_product.id,
            quantity=2,
            expires_at=datetime.now(UTC) + timedelta(minutes=5),
        )
    )
    db.flush()
    assert sale_product.available_quantity == 8

    client.post("/api/v1/auth/me/delete", json={"email": user.email})

    db.refresh(sale_product)
    assert sale_product.available_quantity == 10


def test_an_expired_hold_does_not_give_stock_back_twice(client: TestClient, db: Session) -> None:
    """An expired hold has already stopped counting against the sale, so
    releasing it again would hand back units the sale never lost."""
    user = signed_in(client, db)
    sale_product = make_sale_product(db, allocated=10, max_per_user=2)
    reservation = Reservation(
        user_id=user.id,
        flash_sale_product_id=sale_product.id,
        quantity=2,
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
    )
    db.add(reservation)
    db.flush()
    # Wind both timestamps back together; the schema forbids expiring before creation.
    past = datetime.now(UTC) - timedelta(hours=2)
    db.execute(
        Reservation.__table__.update()
        .where(Reservation.id == reservation.id)
        .values(created_at=past, expires_at=past + timedelta(minutes=5))
    )
    db.flush()
    db.expire(reservation)

    client.post("/api/v1/auth/me/delete", json={"email": user.email})

    db.refresh(sale_product)
    assert sale_product.available_quantity == 10


def test_a_stranger_cannot_close_an_account(client: TestClient) -> None:
    response = client.post("/api/v1/auth/me/delete", json={"email": "someone@example.com"})

    assert response.status_code == 401
