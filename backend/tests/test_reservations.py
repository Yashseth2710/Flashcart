"""Holding sale stock: who gets it, for how long, and what happens when they don't come back."""

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import create_access_token, hash_password
from app.models import Reservation, User
from app.models.enums import ReservationStatus
from app.services.reservation import ReservationService
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
) -> Reservation:
    """Places a hold directly, including the counter move a real one would make.

    created_at is set here rather than left to the database, because a hold that
    has already lapsed must still have been created before it expired.
    """
    moment = datetime.now(UTC)
    expires_at = moment + expires_in
    reservation = Reservation(
        user_id=user.id,
        flash_sale_product_id=entry.id,
        quantity=quantity,
        status=ReservationStatus.ACTIVE,
        expires_at=expires_at,
        created_at=min(moment, expires_at - timedelta(seconds=1)),
    )
    entry.reserved_quantity += quantity
    db.add(reservation)
    db.flush()
    return reservation


# Placing a hold


def test_holding_stock_takes_it_off_the_shelf(client: TestClient, db: Session) -> None:
    signed_in(client, db)
    entry = make_sale_product(db, allocated=5, max_per_user=3)

    response = client.post("/api/v1/holds", json={"sale_product_id": str(entry.id), "quantity": 2})

    assert response.status_code == 201
    body = response.json()
    assert body["quantity"] == 2
    assert body["status"] == "ACTIVE"
    assert body["seconds_remaining"] > 0

    db.refresh(entry)
    assert entry.reserved_quantity == 2
    assert entry.available_quantity == 3


def test_the_line_total_reflects_the_sale_price(client: TestClient, db: Session) -> None:
    signed_in(client, db)
    entry = make_sale_product(db, allocated=5, max_per_user=3)

    body = client.post(
        "/api/v1/holds", json={"sale_product_id": str(entry.id), "quantity": 3}
    ).json()

    assert body["sale_price"] == "50.00"
    assert body["line_total"] == "150.00"


def test_you_cannot_hold_more_than_is_left(client: TestClient, db: Session) -> None:
    signed_in(client, db)
    entry = make_sale_product(db, allocated=5, reserved=4, max_per_user=5)

    response = client.post("/api/v1/holds", json={"sale_product_id": str(entry.id), "quantity": 2})

    assert response.status_code == 409
    assert "Only 1 left" in response.json()["detail"]

    db.refresh(entry)
    assert entry.reserved_quantity == 4


def test_a_sold_out_item_says_so(client: TestClient, db: Session) -> None:
    signed_in(client, db)
    entry = make_sale_product(db, allocated=3, reserved=3, max_per_user=3)

    response = client.post("/api/v1/holds", json={"sale_product_id": str(entry.id), "quantity": 1})

    assert response.status_code == 409
    assert "sold out" in response.json()["detail"]


def test_stock_already_sold_is_not_offered_again(client: TestClient, db: Session) -> None:
    signed_in(client, db)
    entry = make_sale_product(db, allocated=4, sold=4, max_per_user=4)

    assert (
        client.post(
            "/api/v1/holds", json={"sale_product_id": str(entry.id), "quantity": 1}
        ).status_code
        == 409
    )


def test_a_hold_needs_at_least_one_unit(client: TestClient, db: Session) -> None:
    signed_in(client, db)
    entry = make_sale_product(db)

    assert (
        client.post(
            "/api/v1/holds", json={"sale_product_id": str(entry.id), "quantity": 0}
        ).status_code
        == 422
    )


def test_a_stranger_cannot_hold_anything(client: TestClient, db: Session) -> None:
    entry = make_sale_product(db)

    assert (
        client.post(
            "/api/v1/holds", json={"sale_product_id": str(entry.id), "quantity": 1}
        ).status_code
        == 401
    )


def test_holding_something_that_does_not_exist(client: TestClient, db: Session) -> None:
    signed_in(client, db)
    import uuid

    response = client.post(
        "/api/v1/holds", json={"sale_product_id": str(uuid.uuid4()), "quantity": 1}
    )

    assert response.status_code == 404


# The selling window


def test_you_cannot_hold_before_the_sale_starts(client: TestClient, db: Session) -> None:
    signed_in(client, db)
    entry = make_sale_product(db, starts_in=timedelta(minutes=5))

    response = client.post("/api/v1/holds", json={"sale_product_id": str(entry.id), "quantity": 1})

    assert response.status_code == 409
    assert "not started" in response.json()["detail"]


def test_you_cannot_hold_after_the_sale_ends(client: TestClient, db: Session) -> None:
    signed_in(client, db)
    entry = make_sale_product(db, starts_in=timedelta(minutes=-60), runs_for=timedelta(minutes=30))

    response = client.post("/api/v1/holds", json={"sale_product_id": str(entry.id), "quantity": 1})

    assert response.status_code == 409
    assert "ended" in response.json()["detail"]


# Per-person limits


def test_the_limit_stops_a_single_greedy_hold(client: TestClient, db: Session) -> None:
    signed_in(client, db)
    entry = make_sale_product(db, allocated=10, max_per_user=2)

    response = client.post("/api/v1/holds", json={"sale_product_id": str(entry.id), "quantity": 3})

    assert response.status_code == 409
    assert "limit of 2" in response.json()["detail"]


def test_the_limit_counts_holds_added_up(client: TestClient, db: Session) -> None:
    signed_in(client, db)
    entry = make_sale_product(db, allocated=10, max_per_user=2)

    client.post("/api/v1/holds", json={"sale_product_id": str(entry.id), "quantity": 1})
    second = client.post("/api/v1/holds", json={"sale_product_id": str(entry.id), "quantity": 2})

    assert second.status_code == 409
    assert "already have 1" in second.json()["detail"]


def test_you_may_hold_right_up_to_the_limit(client: TestClient, db: Session) -> None:
    signed_in(client, db)
    entry = make_sale_product(db, allocated=10, max_per_user=2)

    client.post("/api/v1/holds", json={"sale_product_id": str(entry.id), "quantity": 1})
    second = client.post("/api/v1/holds", json={"sale_product_id": str(entry.id), "quantity": 1})

    assert second.status_code == 201
    db.refresh(entry)
    assert entry.reserved_quantity == 2


def test_a_lapsed_hold_frees_the_limit_again(client: TestClient, db: Session) -> None:
    """Time ran out, so it no longer counts against what they may take."""
    user = signed_in(client, db)
    entry = make_sale_product(db, allocated=10, max_per_user=1)
    hold_for(db, user, entry, expires_in=timedelta(minutes=-1))

    response = client.post("/api/v1/holds", json={"sale_product_id": str(entry.id), "quantity": 1})

    assert response.status_code == 201


def test_the_limit_is_per_person_not_per_sale(client: TestClient, db: Session) -> None:
    other = make_user(db)
    entry = make_sale_product(db, allocated=10, max_per_user=1)
    hold_for(db, other, entry)

    signed_in(client, db)
    response = client.post("/api/v1/holds", json={"sale_product_id": str(entry.id), "quantity": 1})

    assert response.status_code == 201


# Expiry read from the clock


def test_a_lapsed_hold_reads_as_expired_without_a_sweep(client: TestClient, db: Session) -> None:
    """Nothing has marked the row. The clock alone decides."""
    user = signed_in(client, db)
    entry = make_sale_product(db, allocated=5)
    hold = hold_for(db, user, entry, expires_in=timedelta(seconds=-1))
    assert hold.status is ReservationStatus.ACTIVE

    body = client.get(f"/api/v1/holds/{hold.id}").json()

    assert body["status"] == "EXPIRED"
    assert body["seconds_remaining"] == 0


def test_lapsed_stock_is_reclaimed_by_the_next_person(client: TestClient, db: Session) -> None:
    """The whole allocation is spoken for, but the hold on it has run out."""
    abandoner = make_user(db)
    entry = make_sale_product(db, allocated=1, max_per_user=1)
    hold_for(db, abandoner, entry, expires_in=timedelta(minutes=-1))
    assert entry.available_quantity == 0

    signed_in(client, db)
    response = client.post("/api/v1/holds", json={"sale_product_id": str(entry.id), "quantity": 1})

    assert response.status_code == 201
    db.refresh(entry)
    assert entry.reserved_quantity == 1


def test_a_live_hold_is_not_taken_from_its_owner(client: TestClient, db: Session) -> None:
    holder = make_user(db)
    entry = make_sale_product(db, allocated=1, max_per_user=1)
    hold_for(db, holder, entry, expires_in=timedelta(minutes=9))

    signed_in(client, db)
    response = client.post("/api/v1/holds", json={"sale_product_id": str(entry.id), "quantity": 1})

    assert response.status_code == 409


def test_the_sweep_marks_lapsed_holds_and_returns_their_stock(db: Session) -> None:
    user = make_user(db)
    entry = make_sale_product(db, allocated=5)
    hold = hold_for(db, user, entry, quantity=2, expires_in=timedelta(minutes=-1))

    swept = ReservationService(db).sweep()

    assert swept >= 1
    db.refresh(hold)
    db.refresh(entry)
    assert hold.status is ReservationStatus.EXPIRED
    assert entry.reserved_quantity == 0


def test_the_sweep_leaves_live_holds_alone(db: Session) -> None:
    user = make_user(db)
    entry = make_sale_product(db, allocated=5)
    hold = hold_for(db, user, entry, quantity=2)

    ReservationService(db).sweep()

    db.refresh(hold)
    assert hold.status is ReservationStatus.ACTIVE
    assert entry.reserved_quantity == 2


def test_sweeping_twice_does_not_return_stock_twice(db: Session) -> None:
    user = make_user(db)
    entry = make_sale_product(db, allocated=5)
    hold_for(db, user, entry, quantity=2, expires_in=timedelta(minutes=-1))

    service = ReservationService(db)
    service.sweep()
    service.sweep()

    db.refresh(entry)
    assert entry.reserved_quantity == 0


# Letting a hold go


def test_releasing_a_hold_puts_the_stock_back(client: TestClient, db: Session) -> None:
    user = signed_in(client, db)
    entry = make_sale_product(db, allocated=5)
    hold = hold_for(db, user, entry, quantity=2)

    response = client.post(f"/api/v1/holds/{hold.id}/release")

    assert response.status_code == 200
    assert response.json()["status"] == "CANCELLED"
    db.refresh(entry)
    assert entry.reserved_quantity == 0


def test_a_released_hold_cannot_be_released_again(client: TestClient, db: Session) -> None:
    user = signed_in(client, db)
    entry = make_sale_product(db, allocated=5)
    hold = hold_for(db, user, entry)

    client.post(f"/api/v1/holds/{hold.id}/release")
    second = client.post(f"/api/v1/holds/{hold.id}/release")

    assert second.status_code == 409
    assert "let go" in second.json()["detail"]

    db.refresh(entry)
    assert entry.reserved_quantity == 0


def test_releasing_a_lapsed_hold_says_time_ran_out(client: TestClient, db: Session) -> None:
    user = signed_in(client, db)
    entry = make_sale_product(db, allocated=5)
    hold = hold_for(db, user, entry, expires_in=timedelta(seconds=-1))

    response = client.post(f"/api/v1/holds/{hold.id}/release")

    assert response.status_code == 409
    assert "run out of time" in response.json()["detail"]

    # Still handed back, and only once.
    db.refresh(entry)
    assert entry.reserved_quantity == 0


def test_you_cannot_release_someone_elses_hold(client: TestClient, db: Session) -> None:
    other = make_user(db)
    entry = make_sale_product(db, allocated=5)
    hold = hold_for(db, other, entry)

    signed_in(client, db)
    response = client.post(f"/api/v1/holds/{hold.id}/release")

    assert response.status_code == 404
    db.refresh(entry)
    assert entry.reserved_quantity == 1


# Reading your own holds


def test_your_holds_list_shows_what_you_have(client: TestClient, db: Session) -> None:
    user = signed_in(client, db)
    entry = make_sale_product(db, allocated=5, max_per_user=3)
    hold_for(db, user, entry, quantity=2)

    body = client.get("/api/v1/holds").json()

    assert len(body) == 1
    assert body[0]["quantity"] == 2
    assert body[0]["product_name"] == "Test Product"
    assert body[0]["sale_name"] == "Test Sale"


def test_your_holds_list_leaves_out_other_people(client: TestClient, db: Session) -> None:
    other = make_user(db)
    entry = make_sale_product(db, allocated=5)
    hold_for(db, other, entry)

    signed_in(client, db)

    assert client.get("/api/v1/holds").json() == []


def test_you_cannot_read_someone_elses_hold(client: TestClient, db: Session) -> None:
    other = make_user(db)
    entry = make_sale_product(db, allocated=5)
    hold = hold_for(db, other, entry)

    signed_in(client, db)

    assert client.get(f"/api/v1/holds/{hold.id}").status_code == 404


def test_a_stranger_has_no_holds_to_read(client: TestClient) -> None:
    assert client.get("/api/v1/holds").status_code == 401


# The database has the last word


def test_the_counters_can_never_exceed_the_allocation(client: TestClient, db: Session) -> None:
    """Whatever the application believes, the row refuses to oversell."""
    signed_in(client, db)
    entry = make_sale_product(db, allocated=2, max_per_user=5)

    first = client.post("/api/v1/holds", json={"sale_product_id": str(entry.id), "quantity": 2})
    second = client.post("/api/v1/holds", json={"sale_product_id": str(entry.id), "quantity": 1})

    assert first.status_code == 201
    assert second.status_code == 409

    db.refresh(entry)
    assert entry.reserved_quantity + entry.sold_quantity <= entry.allocated_quantity
