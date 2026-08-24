"""Buying a hold: what is charged, what moves, and what a retry does."""

import uuid
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import create_access_token, hash_password
from app.models import Order, Reservation, User
from app.models.enums import OrderStatus, ReservationStatus
from app.services.payment import ALWAYS_DECLINES
from tests.factories import make_sale_product, make_user

PASSWORD = "a-long-enough-password"


def signed_in(client: TestClient, db: Session) -> User:
    user = make_user(db)
    user.password_hash = hash_password(PASSWORD)
    db.flush()
    client.cookies.set(get_settings().cookie_name, create_access_token(str(user.id), "CUSTOMER"))
    return user


def hold_for(
    db: Session,
    user: User,
    entry,
    *,
    quantity: int = 1,
    expires_in: timedelta = timedelta(minutes=10),
    status: ReservationStatus = ReservationStatus.ACTIVE,
) -> Reservation:
    moment = datetime.now(UTC)
    expires_at = moment + expires_in
    reservation = Reservation(
        user_id=user.id,
        flash_sale_product_id=entry.id,
        quantity=quantity,
        status=status,
        expires_at=expires_at,
        created_at=min(moment, expires_at - timedelta(seconds=1)),
    )
    if status is ReservationStatus.ACTIVE:
        entry.reserved_quantity += quantity
    db.add(reservation)
    db.flush()
    return reservation


def orders_of(db: Session, user: User) -> int:
    """This person's orders only.

    The suite runs against the same database the app does, which carries real
    rows from driving the running server. Counting globally would pick those up.
    """
    return db.scalar(select(func.count()).select_from(Order).where(Order.user_id == user.id)) or 0


def buy(client: TestClient, hold: Reservation, *, key: str | None = None, card: str | None = None):
    body: dict[str, object] = {
        "reservation_id": str(hold.id),
        "idempotency_key": key or f"key-{uuid.uuid4().hex}",
    }
    if card is not None:
        body["card_number"] = card
    return client.post("/api/v1/orders", json=body)


# Buying


def test_buying_a_hold_moves_the_stock_from_held_to_sold(client: TestClient, db: Session) -> None:
    user = signed_in(client, db)
    entry = make_sale_product(db, allocated=5, max_per_user=3)
    hold = hold_for(db, user, entry, quantity=2)

    response = buy(client, hold)

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "PAID"
    assert body["subtotal"] == "100.00"
    assert body["total"] == "100.00"

    db.refresh(entry)
    assert entry.reserved_quantity == 0
    assert entry.sold_quantity == 2
    # The total committed is unchanged: the units moved across, not in.
    assert entry.available_quantity == 3


def test_the_order_lists_what_was_bought(client: TestClient, db: Session) -> None:
    user = signed_in(client, db)
    entry = make_sale_product(db, allocated=5, max_per_user=3)
    hold = hold_for(db, user, entry, quantity=2)

    body = buy(client, hold).json()

    assert len(body["items"]) == 1
    line = body["items"][0]
    assert line["product_name"] == "Test Product"
    assert line["price"] == "50.00"
    assert line["quantity"] == 2
    assert line["line_total"] == "100.00"
    assert body["sale_name"] == "Test Sale"


def test_the_hold_is_marked_bought(client: TestClient, db: Session) -> None:
    user = signed_in(client, db)
    entry = make_sale_product(db, allocated=5)
    hold = hold_for(db, user, entry)

    buy(client, hold)

    db.refresh(hold)
    assert hold.status is ReservationStatus.COMPLETED


def test_a_bought_hold_no_longer_counts_as_counting_down(client: TestClient, db: Session) -> None:
    user = signed_in(client, db)
    entry = make_sale_product(db, allocated=5)
    hold = hold_for(db, user, entry)

    buy(client, hold)

    body = client.get(f"/api/v1/holds/{hold.id}").json()
    assert body["status"] == "COMPLETED"
    assert body["seconds_remaining"] == 0


# What cannot be bought


def test_you_cannot_buy_a_hold_that_ran_out(client: TestClient, db: Session) -> None:
    user = signed_in(client, db)
    entry = make_sale_product(db, allocated=5)
    hold = hold_for(db, user, entry, expires_in=timedelta(seconds=-1))

    response = buy(client, hold)

    assert response.status_code == 409
    assert "run out of time" in response.json()["detail"]

    # And the stock it was sitting on goes back rather than being stranded.
    db.refresh(entry)
    assert entry.reserved_quantity == 0
    assert entry.sold_quantity == 0


def test_you_cannot_buy_a_hold_you_let_go(client: TestClient, db: Session) -> None:
    user = signed_in(client, db)
    entry = make_sale_product(db, allocated=5)
    hold = hold_for(db, user, entry, status=ReservationStatus.CANCELLED)

    response = buy(client, hold)

    assert response.status_code == 409
    assert "let go" in response.json()["detail"]


def test_you_cannot_buy_someone_elses_hold(client: TestClient, db: Session) -> None:
    other = make_user(db)
    entry = make_sale_product(db, allocated=5)
    hold = hold_for(db, other, entry)

    signed_in(client, db)
    response = buy(client, hold)

    assert response.status_code == 404
    db.refresh(entry)
    assert entry.sold_quantity == 0


def test_buying_a_hold_that_does_not_exist(client: TestClient, db: Session) -> None:
    signed_in(client, db)

    response = client.post(
        "/api/v1/orders",
        json={"reservation_id": str(uuid.uuid4()), "idempotency_key": "a-long-enough-key"},
    )

    assert response.status_code == 404


def test_a_stranger_cannot_buy_anything(client: TestClient, db: Session) -> None:
    user = make_user(db)
    entry = make_sale_product(db, allocated=5)
    hold = hold_for(db, user, entry)

    assert buy(client, hold).status_code == 401


def test_a_key_must_be_long_enough_to_be_meaningful(client: TestClient, db: Session) -> None:
    user = signed_in(client, db)
    entry = make_sale_product(db, allocated=5)
    hold = hold_for(db, user, entry)

    response = client.post(
        "/api/v1/orders", json={"reservation_id": str(hold.id), "idempotency_key": "short"}
    )

    assert response.status_code == 422


# Paying


def test_a_declined_card_charges_nothing_and_keeps_the_hold(
    client: TestClient, db: Session
) -> None:
    user = signed_in(client, db)
    entry = make_sale_product(db, allocated=5)
    hold = hold_for(db, user, entry, quantity=2)

    response = buy(client, hold, card=ALWAYS_DECLINES)

    assert response.status_code == 402
    assert "declined" in response.json()["detail"]

    db.refresh(hold)
    db.refresh(entry)
    # The hold survives so they can try another card.
    assert hold.status is ReservationStatus.ACTIVE
    assert entry.reserved_quantity == 2
    assert entry.sold_quantity == 0
    assert orders_of(db, user) == 0


def test_a_decline_does_not_burn_the_key(client: TestClient, db: Session) -> None:
    """Trying again with the same key after a decline must be allowed."""
    user = signed_in(client, db)
    entry = make_sale_product(db, allocated=5)
    hold = hold_for(db, user, entry)
    key = f"key-{uuid.uuid4().hex}"

    assert buy(client, hold, key=key, card=ALWAYS_DECLINES).status_code == 402
    second = buy(client, hold, key=key)

    assert second.status_code == 201


# Retrying


def test_repeating_a_checkout_returns_the_same_order(client: TestClient, db: Session) -> None:
    user = signed_in(client, db)
    entry = make_sale_product(db, allocated=5, max_per_user=2)
    hold = hold_for(db, user, entry, quantity=2)
    key = f"key-{uuid.uuid4().hex}"

    first = buy(client, hold, key=key)
    second = buy(client, hold, key=key)

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]

    # Charged once, and the stock moved once.
    assert orders_of(db, user) == 1
    db.refresh(entry)
    assert entry.sold_quantity == 2


def test_a_second_checkout_with_a_fresh_key_still_cannot_buy_it_twice(
    client: TestClient, db: Session
) -> None:
    """The unique index is the guarantee, whatever key is presented."""
    user = signed_in(client, db)
    entry = make_sale_product(db, allocated=5)
    hold = hold_for(db, user, entry)

    first = buy(client, hold)
    second = buy(client, hold)

    assert first.status_code == 201
    assert second.status_code in (200, 201, 409)
    assert orders_of(db, user) == 1
    db.refresh(entry)
    assert entry.sold_quantity == 1


def test_reusing_a_key_for_a_different_hold_is_refused(client: TestClient, db: Session) -> None:
    user = signed_in(client, db)
    entry = make_sale_product(db, allocated=5, max_per_user=2)
    first_hold = hold_for(db, user, entry)
    second_hold = hold_for(db, user, entry)
    key = f"key-{uuid.uuid4().hex}"

    assert buy(client, first_hold, key=key).status_code == 201
    clash = buy(client, second_hold, key=key)

    assert clash.status_code == 409
    assert "different order" in clash.json()["detail"]
    # The second hold is untouched, so it can still be bought properly.
    db.refresh(second_hold)
    assert second_hold.status is ReservationStatus.ACTIVE


def test_buying_a_hold_you_already_bought_returns_that_order(
    client: TestClient, db: Session
) -> None:
    """A retry landing after the first one finished is the same purchase.

    Reporting the hold as taken would be true but useless: it was taken by this
    same person, a moment ago, by this same request.
    """
    user = signed_in(client, db)
    entry = make_sale_product(db, allocated=5)
    hold = hold_for(db, user, entry)

    first = buy(client, hold)
    # A different key, so the idempotency record cannot answer it. The hold
    # itself is what says the purchase already happened.
    again = buy(client, hold)

    assert first.status_code == 201
    assert again.status_code == 201
    assert again.json()["id"] == first.json()["id"]
    assert orders_of(db, user) == 1


def test_someone_else_cannot_ride_a_bought_hold(client: TestClient, db: Session) -> None:
    """Returning the order is only right for the person who bought it."""
    other = make_user(db)
    entry = make_sale_product(db, allocated=5)
    hold = hold_for(db, other, entry)
    hold.status = ReservationStatus.COMPLETED
    db.flush()

    signed_in(client, db)

    assert buy(client, hold).status_code == 404


# Reading your own orders


def test_your_orders_list_shows_what_you_bought(client: TestClient, db: Session) -> None:
    user = signed_in(client, db)
    entry = make_sale_product(db, allocated=5)
    hold = hold_for(db, user, entry)
    buy(client, hold)

    body = client.get("/api/v1/orders").json()

    assert len(body) == 1
    assert body[0]["items"][0]["product_name"] == "Test Product"


def test_your_orders_list_leaves_out_other_people(client: TestClient, db: Session) -> None:
    other = make_user(db)
    entry = make_sale_product(db, allocated=5)
    other_hold = hold_for(db, other, entry)
    other_order = Order(
        user_id=other.id,
        reservation_id=other_hold.id,
        status=OrderStatus.PAID,
        subtotal=1,
        total=1,
    )
    db.add(other_order)
    db.flush()

    signed_in(client, db)

    assert client.get("/api/v1/orders").json() == []


def test_you_cannot_read_someone_elses_order(client: TestClient, db: Session) -> None:
    other = make_user(db)
    entry = make_sale_product(db, allocated=5)
    other_hold = hold_for(db, other, entry)
    order = Order(
        user_id=other.id,
        reservation_id=other_hold.id,
        status=OrderStatus.PAID,
        subtotal=1,
        total=1,
    )
    db.add(order)
    db.flush()

    signed_in(client, db)

    assert client.get(f"/api/v1/orders/{order.id}").status_code == 404


def test_a_stranger_has_no_orders_to_read(client: TestClient) -> None:
    assert client.get("/api/v1/orders").status_code == 401


# The database has the last word


def test_the_invariant_survives_a_sale_selling_out(client: TestClient, db: Session) -> None:
    user = signed_in(client, db)
    entry = make_sale_product(db, allocated=2, max_per_user=2)
    hold = hold_for(db, user, entry, quantity=2)

    assert buy(client, hold).status_code == 201

    db.refresh(entry)
    assert entry.reserved_quantity == 0
    assert entry.sold_quantity == 2
    assert entry.available_quantity == 0
    assert entry.reserved_quantity + entry.sold_quantity <= entry.allocated_quantity
