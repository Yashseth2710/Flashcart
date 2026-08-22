"""Sales, the stock they hold, and who may set them up."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import create_access_token
from app.models import FlashSale, Inventory, Product, ProductVariant, UserRole
from tests.factories import make_user, unique


def sale_window(*, starts_in: timedelta, runs_for: timedelta = timedelta(minutes=30)):
    start = datetime.now(UTC) + starts_in
    return {"start_time": start.isoformat(), "end_time": (start + runs_for).isoformat()}


@pytest.fixture
def stocked_variant(db: Session) -> ProductVariant:
    product = Product(name="Sale Bed", slug=unique("sale-bed"), base_price=Decimal("1899.99"))
    variant = ProductVariant(
        product=product, sku=unique("SKU"), name="Standard", price=Decimal("1899.99")
    )
    db.add_all([product, variant, Inventory(variant=variant, total_quantity=88)])
    db.flush()
    return variant


@pytest.fixture
def admin(client: TestClient, db: Session) -> None:
    user = make_user(db, role=UserRole.ADMIN)
    client.cookies.set(get_settings().cookie_name, create_access_token(str(user.id), "ADMIN"))


def create_sale(client: TestClient, **window) -> str:
    response = client.post(
        "/api/v1/admin/flash-sales",
        json={"name": "Tech Rush", **(window or sale_window(starts_in=timedelta(minutes=5)))},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def add_item(client: TestClient, sale_id: str, variant: ProductVariant, **overrides):
    payload = {
        "variant_id": str(variant.id),
        "sale_price": "999.99",
        "allocated_quantity": 20,
        "max_per_user": 2,
        **overrides,
    }
    return client.post(f"/api/v1/admin/flash-sales/{sale_id}/items", json=payload)


# What a sale's status means


def test_a_sale_before_its_start_is_upcoming(db: Session) -> None:
    start = datetime.now(UTC) + timedelta(hours=1)
    sale = FlashSale(name="Later", start_time=start, end_time=start + timedelta(hours=1))

    assert sale.status_at(datetime.now(UTC)) == "UPCOMING"


def test_a_sale_inside_its_window_is_active(db: Session) -> None:
    start = datetime.now(UTC) - timedelta(minutes=5)
    sale = FlashSale(name="Now", start_time=start, end_time=start + timedelta(hours=1))

    assert sale.status_at(datetime.now(UTC)) == "ACTIVE"
    assert sale.is_running_at(datetime.now(UTC)) is True


def test_a_sale_past_its_end_has_ended(db: Session) -> None:
    start = datetime.now(UTC) - timedelta(hours=2)
    sale = FlashSale(name="Over", start_time=start, end_time=start + timedelta(hours=1))

    assert sale.status_at(datetime.now(UTC)) == "ENDED"
    assert sale.is_running_at(datetime.now(UTC)) is False


def test_a_sale_starts_the_instant_its_start_time_arrives(db: Session) -> None:
    """The boundary belongs to the sale, so nobody is told to wait a moment longer."""
    start = datetime.now(UTC)
    sale = FlashSale(name="Edge", start_time=start, end_time=start + timedelta(hours=1))

    assert sale.status_at(start) == "ACTIVE"


def test_a_sale_is_over_the_instant_its_end_time_arrives(db: Session) -> None:
    start = datetime.now(UTC) - timedelta(hours=1)
    end = datetime.now(UTC)
    sale = FlashSale(name="Edge", start_time=start, end_time=end)

    assert sale.status_at(end) == "ENDED"


# Setting a sale up


def test_an_admin_creates_a_sale(client: TestClient, admin: None) -> None:
    body = client.post(
        "/api/v1/admin/flash-sales",
        json={"name": "Tech Rush", **sale_window(starts_in=timedelta(minutes=5))},
    ).json()

    assert body["name"] == "Tech Rush"
    assert body["status"] == "UPCOMING"
    assert body["items"] == []


def test_a_sale_must_end_after_it_starts(client: TestClient, admin: None) -> None:
    start = datetime.now(UTC) + timedelta(hours=1)

    response = client.post(
        "/api/v1/admin/flash-sales",
        json={
            "name": "Backwards",
            "start_time": start.isoformat(),
            "end_time": (start - timedelta(minutes=1)).isoformat(),
        },
    )

    assert response.status_code == 422


def test_a_stranger_cannot_create_a_sale(client: TestClient) -> None:
    response = client.post(
        "/api/v1/admin/flash-sales",
        json={"name": "X", **sale_window(starts_in=timedelta(minutes=5))},
    )

    assert response.status_code == 401


def test_a_customer_cannot_create_a_sale(client: TestClient, db: Session) -> None:
    user = make_user(db, role=UserRole.CUSTOMER)
    client.cookies.set(get_settings().cookie_name, create_access_token(str(user.id), "CUSTOMER"))

    response = client.post(
        "/api/v1/admin/flash-sales",
        json={"name": "X", **sale_window(starts_in=timedelta(minutes=5))},
    )

    assert response.status_code == 403


# Stock moving into and out of a sale


def test_adding_a_product_takes_its_stock_out_of_the_warehouse(
    client: TestClient, admin: None, stocked_variant: ProductVariant, db: Session
) -> None:
    """The shop must not be able to sell what a sale has already promised."""
    sale_id = create_sale(client)

    response = add_item(client, sale_id, stocked_variant, allocated_quantity=20)

    assert response.status_code == 200
    db.refresh(stocked_variant.inventory)
    assert stocked_variant.inventory.available_quantity == 68
    assert stocked_variant.inventory.total_quantity == 88


def test_a_sale_item_carries_its_own_price_and_limit(
    client: TestClient, admin: None, stocked_variant: ProductVariant
) -> None:
    sale_id = create_sale(client)

    item = add_item(client, sale_id, stocked_variant, sale_price="999.99", max_per_user=2).json()[
        "items"
    ][0]

    assert item["normal_price"] == "1899.99"
    assert item["sale_price"] == "999.99"
    assert item["available_quantity"] == 20
    assert item["max_per_user"] == 2


def test_a_sale_cannot_promise_stock_the_warehouse_does_not_have(
    client: TestClient, admin: None, stocked_variant: ProductVariant
) -> None:
    sale_id = create_sale(client)

    response = add_item(client, sale_id, stocked_variant, allocated_quantity=1000)

    assert response.status_code == 409
    assert "88" in response.json()["detail"]


def test_the_same_product_cannot_be_added_twice(
    client: TestClient, admin: None, stocked_variant: ProductVariant
) -> None:
    sale_id = create_sale(client)
    add_item(client, sale_id, stocked_variant)

    response = add_item(client, sale_id, stocked_variant)

    assert response.status_code == 409


def test_two_sales_may_each_hold_their_own_share(
    client: TestClient, admin: None, stocked_variant: ProductVariant, db: Session
) -> None:
    first = create_sale(client)
    second = create_sale(client)

    add_item(client, first, stocked_variant, allocated_quantity=30)
    add_item(client, second, stocked_variant, allocated_quantity=40)

    db.refresh(stocked_variant.inventory)
    assert stocked_variant.inventory.available_quantity == 18


def test_nobody_can_be_allowed_more_than_the_sale_holds(
    client: TestClient, admin: None, stocked_variant: ProductVariant
) -> None:
    sale_id = create_sale(client)

    response = add_item(client, sale_id, stocked_variant, allocated_quantity=5, max_per_user=10)

    assert response.status_code == 422


def test_removing_a_product_gives_its_stock_back(
    client: TestClient, admin: None, stocked_variant: ProductVariant, db: Session
) -> None:
    sale_id = create_sale(client)
    item_id = add_item(client, sale_id, stocked_variant, allocated_quantity=20).json()["items"][0][
        "id"
    ]

    client.delete(f"/api/v1/admin/flash-sales/{sale_id}/items/{item_id}")

    db.refresh(stocked_variant.inventory)
    assert stocked_variant.inventory.available_quantity == 88


def test_stock_a_shopper_is_holding_cannot_be_pulled_away(
    client: TestClient, admin: None, stocked_variant: ProductVariant, db: Session
) -> None:
    sale_id = create_sale(client)
    added = add_item(client, sale_id, stocked_variant).json()["items"][0]
    from app.models import FlashSaleProduct

    entry = db.get(FlashSaleProduct, added["id"])
    entry.reserved_quantity = 3
    db.flush()

    response = client.delete(f"/api/v1/admin/flash-sales/{sale_id}/items/{added['id']}")

    assert response.status_code == 409
    assert "3" in response.json()["detail"]


def test_a_product_cannot_be_added_once_the_sale_is_running(
    client: TestClient, admin: None, stocked_variant: ProductVariant
) -> None:
    """Changing the shelf while people are buying from it invites confusion."""
    sale_id = create_sale(client, **sale_window(starts_in=timedelta(minutes=-1)))

    response = add_item(client, sale_id, stocked_variant)

    assert response.status_code == 409


def test_cancelling_a_sale_returns_everything_it_held(
    client: TestClient, admin: None, stocked_variant: ProductVariant, db: Session
) -> None:
    sale_id = create_sale(client)
    add_item(client, sale_id, stocked_variant, allocated_quantity=25)

    response = client.delete(f"/api/v1/admin/flash-sales/{sale_id}")

    assert response.status_code == 204
    db.refresh(stocked_variant.inventory)
    assert stocked_variant.inventory.available_quantity == 88


# What shoppers see


def test_the_shop_lists_a_coming_sale(
    client: TestClient, admin: None, stocked_variant: ProductVariant
) -> None:
    sale_id = create_sale(client)
    add_item(client, sale_id, stocked_variant)

    listed = client.get("/api/v1/flash-sales").json()

    assert any(sale["id"] == sale_id for sale in listed)


def test_a_finished_sale_is_not_listed(client: TestClient, admin: None) -> None:
    sale_id = create_sale(
        client, **sale_window(starts_in=timedelta(hours=-3), runs_for=timedelta(hours=1))
    )

    listed = client.get("/api/v1/flash-sales").json()

    assert all(sale["id"] != sale_id for sale in listed)


def test_a_sale_that_is_on_now_is_reported_as_running(
    client: TestClient, admin: None, stocked_variant: ProductVariant, db: Session
) -> None:
    """Only one sale runs at a time here, so clear the field first."""
    db.query(FlashSale).delete()
    db.flush()
    create_sale(client, **sale_window(starts_in=timedelta(hours=2)))
    running_id = create_sale(client, **sale_window(starts_in=timedelta(minutes=-1)))

    body = client.get("/api/v1/flash-sales/running").json()

    assert body is not None
    assert body["id"] == running_id


def test_there_is_no_running_sale_when_none_is_on(
    client: TestClient, admin: None, db: Session
) -> None:
    db.query(FlashSale).delete()
    db.flush()
    create_sale(client, **sale_window(starts_in=timedelta(hours=5)))

    assert client.get("/api/v1/flash-sales/running").json() is None


def test_asking_for_a_sale_that_does_not_exist(client: TestClient) -> None:
    missing = "00000000-0000-0000-0000-000000000000"

    assert client.get(f"/api/v1/flash-sales/{missing}").status_code == 404


def test_an_admin_sees_finished_sales_too(client: TestClient, admin: None) -> None:
    ended_id = create_sale(
        client, **sale_window(starts_in=timedelta(hours=-3), runs_for=timedelta(hours=1))
    )

    listed = client.get("/api/v1/admin/flash-sales").json()

    assert any(sale["id"] == ended_id and sale["status"] == "ENDED" for sale in listed)
