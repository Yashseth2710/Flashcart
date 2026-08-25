"""Saving things and marking sales: what a shopper does before the doors open."""

import uuid
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import create_access_token, hash_password
from app.models import FlashSale, FlashSaleProduct, SavedProduct, User
from tests.factories import make_sale_product, make_user, make_variant

PASSWORD = "a-long-enough-password"


def signed_in(client: TestClient, db: Session) -> User:
    user = make_user(db)
    user.password_hash = hash_password(PASSWORD)
    db.flush()
    client.cookies.set(get_settings().cookie_name, create_access_token(str(user.id), "CUSTOMER"))
    return user


def save(client: TestClient, product_id) -> object:
    return client.post("/api/v1/saved", json={"product_id": str(product_id)})


# Saving a product


def test_saving_a_product_puts_it_on_the_list(client: TestClient, db: Session) -> None:
    signed_in(client, db)
    variant = make_variant(db)

    response = save(client, variant.product_id)

    assert response.status_code == 201
    body = response.json()
    assert body["product_id"] == str(variant.product_id)
    assert body["product_name"] == "Test Product"
    # Not in a sale, so nothing is claimed about one.
    assert body["sale_id"] is None
    assert body["available_quantity"] is None


def test_saving_the_same_thing_twice_is_the_same_as_once(client: TestClient, db: Session) -> None:
    """A second tap is not a mistake worth an error."""
    user = signed_in(client, db)
    variant = make_variant(db)

    first = save(client, variant.product_id)
    second = save(client, variant.product_id)

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]
    assert len(client.get("/api/v1/saved").json()) == 1
    assert db.query(SavedProduct).filter(SavedProduct.user_id == user.id).count() == 1


def test_saving_something_that_does_not_exist(client: TestClient, db: Session) -> None:
    signed_in(client, db)

    assert save(client, uuid.uuid4()).status_code == 404


def test_a_withdrawn_product_cannot_be_saved(client: TestClient, db: Session) -> None:
    signed_in(client, db)
    variant = make_variant(db)
    variant.product.is_active = False
    db.flush()

    assert save(client, variant.product_id).status_code == 404


def test_a_stranger_cannot_save_anything(client: TestClient, db: Session) -> None:
    variant = make_variant(db)

    assert save(client, variant.product_id).status_code == 401


# Forgetting


def test_forgetting_takes_it_off_the_list(client: TestClient, db: Session) -> None:
    signed_in(client, db)
    variant = make_variant(db)
    save(client, variant.product_id)

    response = client.delete(f"/api/v1/saved/{variant.product_id}")

    assert response.status_code == 204
    assert client.get("/api/v1/saved").json() == []


def test_forgetting_something_never_saved(client: TestClient, db: Session) -> None:
    signed_in(client, db)
    variant = make_variant(db)

    assert client.delete(f"/api/v1/saved/{variant.product_id}").status_code == 404


def test_forgetting_twice_is_refused_the_second_time(client: TestClient, db: Session) -> None:
    signed_in(client, db)
    variant = make_variant(db)
    save(client, variant.product_id)

    assert client.delete(f"/api/v1/saved/{variant.product_id}").status_code == 204
    assert client.delete(f"/api/v1/saved/{variant.product_id}").status_code == 404


# Whose list is whose


def test_your_saved_list_leaves_out_other_people(client: TestClient, db: Session) -> None:
    other = make_user(db)
    variant = make_variant(db)
    db.add(SavedProduct(user_id=other.id, product_id=variant.product_id))
    db.flush()

    signed_in(client, db)

    assert client.get("/api/v1/saved").json() == []


def test_you_cannot_forget_someone_elses_saved_product(client: TestClient, db: Session) -> None:
    other = make_user(db)
    variant = make_variant(db)
    db.add(SavedProduct(user_id=other.id, product_id=variant.product_id))
    db.flush()

    signed_in(client, db)

    assert client.delete(f"/api/v1/saved/{variant.product_id}").status_code == 404
    assert db.query(SavedProduct).filter(SavedProduct.user_id == other.id).count() == 1


def test_a_stranger_has_no_saved_list(client: TestClient) -> None:
    assert client.get("/api/v1/saved").status_code == 401


# A saved product that is in a sale


def test_a_saved_product_says_when_it_is_in_a_running_sale(client: TestClient, db: Session) -> None:
    signed_in(client, db)
    entry = make_sale_product(db, allocated=5, reserved=2)
    product_id = entry.variant.product_id

    body = save(client, product_id).json()

    assert body["sale_id"] == str(entry.flash_sale_id)
    assert body["sale_status"] == "ACTIVE"
    assert body["sale_price"] == "50.00"
    assert body["sale_product_id"] == str(entry.id)
    assert body["available_quantity"] == 3


def test_a_saved_product_in_a_sale_still_to_come_shows_no_count(
    client: TestClient, db: Session
) -> None:
    """Before the doors open there is nothing left, only an allocation."""
    signed_in(client, db)
    entry = make_sale_product(db, allocated=5, starts_in=timedelta(minutes=30))

    body = save(client, entry.variant.product_id).json()

    assert body["sale_status"] == "UPCOMING"
    assert body["available_quantity"] is None
    assert body["starts_at"] is not None


def test_a_finished_sale_is_not_mentioned_on_a_saved_product(
    client: TestClient, db: Session
) -> None:
    signed_in(client, db)
    entry = make_sale_product(db, starts_in=timedelta(hours=-3), runs_for=timedelta(hours=1))

    body = save(client, entry.variant.product_id).json()

    assert body["sale_id"] is None
    assert body["sale_status"] is None


def test_the_soonest_unfinished_sale_is_the_one_shown(client: TestClient, db: Session) -> None:
    """A product can be in several sales; only the next one matters."""
    signed_in(client, db)
    soon = make_sale_product(db, starts_in=timedelta(minutes=10))
    later_start = datetime.now(UTC) + timedelta(days=2)
    later = FlashSale(
        name="Much Later", start_time=later_start, end_time=later_start + timedelta(hours=1)
    )
    db.add(later)
    db.flush()
    db.add(
        FlashSaleProduct(
            flash_sale_id=later.id,
            variant_id=soon.variant_id,
            sale_price=soon.sale_price,
            allocated_quantity=3,
            max_per_user=1,
        )
    )
    db.flush()

    body = save(client, soon.variant.product_id).json()

    assert body["sale_id"] == str(soon.flash_sale_id)


# Reminders


def test_marking_a_sale_to_come_back_to(client: TestClient, db: Session) -> None:
    signed_in(client, db)
    entry = make_sale_product(db, starts_in=timedelta(hours=1))

    response = client.post("/api/v1/reminders", json={"flash_sale_id": str(entry.flash_sale_id)})

    assert response.status_code == 201
    body = response.json()
    assert body["sale_id"] == str(entry.flash_sale_id)
    assert body["status"] == "UPCOMING"
    assert body["item_count"] == 1


def test_marking_the_same_sale_twice_is_the_same_as_once(client: TestClient, db: Session) -> None:
    signed_in(client, db)
    entry = make_sale_product(db, starts_in=timedelta(hours=1))
    payload = {"flash_sale_id": str(entry.flash_sale_id)}

    first = client.post("/api/v1/reminders", json=payload)
    second = client.post("/api/v1/reminders", json=payload)

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]
    assert len(client.get("/api/v1/reminders").json()) == 1


def test_a_sale_that_has_finished_cannot_be_marked(client: TestClient, db: Session) -> None:
    signed_in(client, db)
    entry = make_sale_product(db, starts_in=timedelta(hours=-3), runs_for=timedelta(hours=1))

    response = client.post("/api/v1/reminders", json={"flash_sale_id": str(entry.flash_sale_id)})

    assert response.status_code == 409
    assert "ended" in response.json()["detail"]


def test_a_running_sale_can_still_be_marked(client: TestClient, db: Session) -> None:
    """Useful mid-sale: it is still on, and they may want it in their list."""
    signed_in(client, db)
    entry = make_sale_product(db)

    response = client.post("/api/v1/reminders", json={"flash_sale_id": str(entry.flash_sale_id)})

    assert response.status_code == 201
    assert response.json()["status"] == "ACTIVE"


def test_marking_a_sale_that_does_not_exist(client: TestClient, db: Session) -> None:
    signed_in(client, db)

    assert (
        client.post("/api/v1/reminders", json={"flash_sale_id": str(uuid.uuid4())}).status_code
        == 404
    )


def test_a_reminder_counts_how_many_saved_products_are_in_the_sale(
    client: TestClient, db: Session
) -> None:
    """The reason the reminder was worth setting."""
    signed_in(client, db)
    entry = make_sale_product(db, starts_in=timedelta(hours=1))
    save(client, entry.variant.product_id)

    body = client.post("/api/v1/reminders", json={"flash_sale_id": str(entry.flash_sale_id)}).json()

    assert body["saved_in_sale"] == 1


def test_finished_sales_drop_off_the_reminder_list(client: TestClient, db: Session) -> None:
    signed_in(client, db)
    entry = make_sale_product(db, starts_in=timedelta(minutes=30))
    client.post("/api/v1/reminders", json={"flash_sale_id": str(entry.flash_sale_id)})
    assert len(client.get("/api/v1/reminders").json()) == 1

    # The sale comes and goes.
    sale = db.get(FlashSale, entry.flash_sale_id)
    sale.start_time = datetime.now(UTC) - timedelta(hours=2)
    sale.end_time = datetime.now(UTC) - timedelta(hours=1)
    db.flush()

    assert client.get("/api/v1/reminders").json() == []


def test_reminders_come_back_soonest_first(client: TestClient, db: Session) -> None:
    signed_in(client, db)
    later = make_sale_product(db, starts_in=timedelta(hours=5))
    sooner = make_sale_product(db, starts_in=timedelta(hours=1))

    for entry in (later, sooner):
        client.post("/api/v1/reminders", json={"flash_sale_id": str(entry.flash_sale_id)})

    body = client.get("/api/v1/reminders").json()

    assert [r["sale_id"] for r in body] == [
        str(sooner.flash_sale_id),
        str(later.flash_sale_id),
    ]


def test_unmarking_a_sale(client: TestClient, db: Session) -> None:
    signed_in(client, db)
    entry = make_sale_product(db, starts_in=timedelta(hours=1))
    client.post("/api/v1/reminders", json={"flash_sale_id": str(entry.flash_sale_id)})

    assert client.delete(f"/api/v1/reminders/{entry.flash_sale_id}").status_code == 204
    assert client.get("/api/v1/reminders").json() == []


def test_unmarking_a_sale_never_marked(client: TestClient, db: Session) -> None:
    signed_in(client, db)
    entry = make_sale_product(db)

    assert client.delete(f"/api/v1/reminders/{entry.flash_sale_id}").status_code == 404


def test_a_stranger_has_no_reminders(client: TestClient) -> None:
    assert client.get("/api/v1/reminders").status_code == 401


# What is waiting on arrival


def test_waiting_is_empty_for_someone_who_has_marked_nothing(
    client: TestClient, db: Session
) -> None:
    signed_in(client, db)

    body = client.get("/api/v1/waiting").json()

    assert body == {
        "saved_count": 0,
        "reminder_count": 0,
        "open_now": None,
        "opening_next": None,
    }


def test_waiting_counts_what_has_been_marked(client: TestClient, db: Session) -> None:
    signed_in(client, db)
    variant = make_variant(db)
    save(client, variant.product_id)
    entry = make_sale_product(db, starts_in=timedelta(hours=2))
    client.post("/api/v1/reminders", json={"flash_sale_id": str(entry.flash_sale_id)})

    body = client.get("/api/v1/waiting").json()

    assert body["saved_count"] == 1
    assert body["reminder_count"] == 1
    assert body["opening_next"]["sale_id"] == str(entry.flash_sale_id)
    assert body["open_now"] is None


def test_waiting_singles_out_a_marked_sale_that_is_on_now(client: TestClient, db: Session) -> None:
    """The whole reason for setting a reminder."""
    signed_in(client, db)
    running = make_sale_product(db)
    coming = make_sale_product(db, starts_in=timedelta(hours=3))

    for entry in (running, coming):
        client.post("/api/v1/reminders", json={"flash_sale_id": str(entry.flash_sale_id)})

    body = client.get("/api/v1/waiting").json()

    assert body["open_now"]["sale_id"] == str(running.flash_sale_id)
    assert body["opening_next"]["sale_id"] == str(coming.flash_sale_id)
    assert body["reminder_count"] == 2


def test_a_finished_sale_is_not_waiting_for_anyone(client: TestClient, db: Session) -> None:
    signed_in(client, db)
    entry = make_sale_product(db, starts_in=timedelta(minutes=30))
    client.post("/api/v1/reminders", json={"flash_sale_id": str(entry.flash_sale_id)})

    sale = db.get(FlashSale, entry.flash_sale_id)
    sale.start_time = datetime.now(UTC) - timedelta(hours=2)
    sale.end_time = datetime.now(UTC) - timedelta(hours=1)
    db.flush()

    body = client.get("/api/v1/waiting").json()

    assert body["reminder_count"] == 0
    assert body["open_now"] is None
    assert body["opening_next"] is None


def test_a_stranger_has_nothing_waiting(client: TestClient) -> None:
    assert client.get("/api/v1/waiting").status_code == 401


# Closing an account


def test_closing_an_account_takes_its_marks_with_it(client: TestClient, db: Session) -> None:
    """Neither holds stock, so nothing has to be handed back first."""
    user = signed_in(client, db)
    variant = make_variant(db)
    save(client, variant.product_id)
    entry = make_sale_product(db, starts_in=timedelta(hours=1))
    client.post("/api/v1/reminders", json={"flash_sale_id": str(entry.flash_sale_id)})

    response = client.post("/api/v1/auth/me/delete", json={"email": user.email})

    assert response.status_code == 204
    assert db.query(SavedProduct).filter(SavedProduct.user_id == user.id).count() == 0
