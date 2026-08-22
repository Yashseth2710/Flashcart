"""Browsing the shop, and what only an administrator may change."""

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import create_access_token
from app.models import Inventory, Product, ProductVariant, UserRole
from tests.factories import make_user, unique


@pytest.fixture
def catalogue(db: Session) -> Product:
    product = Product(
        name="Verifiable Lamp",
        slug=unique("verifiable-lamp"),
        category="home-decoration",
        brand="FlashCart",
        base_price=Decimal("49.50"),
    )
    variant = ProductVariant(
        product=product, sku=unique("SKU"), name="Standard", price=Decimal("49.50")
    )
    db.add_all([product, variant, Inventory(variant=variant, total_quantity=20)])
    db.flush()
    return product


def sign_in(client: TestClient, db: Session, role: UserRole) -> None:
    user = make_user(db, role=role)
    client.cookies.set(get_settings().cookie_name, create_access_token(str(user.id), role.value))


def test_browsing_lists_products(client: TestClient, catalogue: Product) -> None:
    body = client.get("/api/v1/products").json()

    assert body["total"] >= 1


def test_searching_matches_a_name(client: TestClient, catalogue: Product) -> None:
    body = client.get("/api/v1/products", params={"search": "Verifiable Lamp"}).json()

    assert [item["slug"] for item in body["items"]] == [catalogue.slug]


def test_searching_matches_a_brand(client: TestClient, catalogue: Product) -> None:
    body = client.get("/api/v1/products", params={"search": "FlashCart"}).json()

    assert catalogue.slug in [item["slug"] for item in body["items"]]


def test_searching_for_nothing_that_exists_returns_an_empty_page(client: TestClient) -> None:
    body = client.get("/api/v1/products", params={"search": "zzzz-no-such-thing"}).json()

    assert body["items"] == []
    assert body["total"] == 0


def test_filtering_by_category(client: TestClient, catalogue: Product) -> None:
    body = client.get("/api/v1/products", params={"category": "home-decoration"}).json()

    assert all(item["category"] == "home-decoration" for item in body["items"])


def test_a_page_reports_the_total_beyond_it(client: TestClient, catalogue: Product) -> None:
    body = client.get("/api/v1/products", params={"limit": 1}).json()

    assert len(body["items"]) <= 1
    assert body["total"] >= 1


def test_an_absurd_page_size_is_refused(client: TestClient) -> None:
    assert client.get("/api/v1/products", params={"limit": 5000}).status_code == 422


def test_a_product_page_shows_its_variants_and_stock(
    client: TestClient, catalogue: Product
) -> None:
    body = client.get(f"/api/v1/products/{catalogue.slug}").json()

    assert body["name"] == "Verifiable Lamp"
    assert len(body["variants"]) == 1
    assert body["variants"][0]["available_quantity"] == 20


def test_a_hidden_product_is_not_shown(client: TestClient, catalogue: Product, db: Session) -> None:
    catalogue.is_active = False
    db.flush()

    assert client.get(f"/api/v1/products/{catalogue.slug}").status_code == 404


def test_asking_for_a_product_that_does_not_exist(client: TestClient) -> None:
    assert client.get("/api/v1/products/no-such-product").status_code == 404


def test_categories_are_listed_for_the_filter(client: TestClient, catalogue: Product) -> None:
    assert "home-decoration" in client.get("/api/v1/products/categories").json()


def test_a_stranger_cannot_add_a_product(client: TestClient) -> None:
    response = client.post("/api/v1/admin/products", json={"name": "X", "base_price": "1.00"})

    assert response.status_code == 401


def test_a_customer_cannot_add_a_product(client: TestClient, db: Session) -> None:
    sign_in(client, db, UserRole.CUSTOMER)

    response = client.post("/api/v1/admin/products", json={"name": "X", "base_price": "1.00"})

    assert response.status_code == 403


def test_an_admin_adds_a_product_with_somewhere_to_put_stock(
    client: TestClient, db: Session
) -> None:
    """A product with no variant has nowhere to hold stock, so one comes with it."""
    sign_in(client, db, UserRole.ADMIN)

    body = client.post(
        "/api/v1/admin/products",
        json={"name": "Brass Table Lamp", "base_price": "80.00", "category": "home-decoration"},
    ).json()

    assert body["slug"].startswith("brass-table-lamp")
    assert len(body["variants"]) == 1
    assert body["variants"][0]["available_quantity"] == 0


def test_two_products_may_share_a_name(client: TestClient, db: Session) -> None:
    sign_in(client, db, UserRole.ADMIN)
    payload = {"name": "Repeated Name", "base_price": "10.00"}

    first = client.post("/api/v1/admin/products", json=payload).json()
    second = client.post("/api/v1/admin/products", json=payload).json()

    assert first["slug"] != second["slug"]


def test_a_negative_price_is_refused(client: TestClient, db: Session) -> None:
    sign_in(client, db, UserRole.ADMIN)

    response = client.post(
        "/api/v1/admin/products", json={"name": "Free Money", "base_price": "-5.00"}
    )

    assert response.status_code == 422


def test_an_admin_edits_a_product(client: TestClient, db: Session, catalogue: Product) -> None:
    sign_in(client, db, UserRole.ADMIN)

    body = client.patch(
        f"/api/v1/admin/products/{catalogue.id}", json={"base_price": "55.00"}
    ).json()

    assert body["base_price"] == "55.00"
    assert body["name"] == "Verifiable Lamp"


def test_hiding_a_product_takes_it_off_the_shop(
    client: TestClient, db: Session, catalogue: Product
) -> None:
    sign_in(client, db, UserRole.ADMIN)

    client.patch(f"/api/v1/admin/products/{catalogue.id}", json={"is_active": False})

    assert client.get(f"/api/v1/products/{catalogue.slug}").status_code == 404


def test_an_admin_sets_stock(client: TestClient, db: Session, catalogue: Product) -> None:
    sign_in(client, db, UserRole.ADMIN)
    variant_id = str(catalogue.variants[0].id)

    body = client.put(
        "/api/v1/admin/stock", json={"variant_id": variant_id, "total_quantity": 75}
    ).json()

    assert body["total_quantity"] == 75
    assert body["available_quantity"] == 75


def test_stock_cannot_be_set_below_what_is_already_committed(
    client: TestClient, db: Session, catalogue: Product
) -> None:
    """Lowering the total below live holds and sales would break the books."""
    inventory = catalogue.variants[0].inventory
    inventory.reserved_quantity = 7
    inventory.sold_quantity = 5
    db.flush()
    sign_in(client, db, UserRole.ADMIN)

    response = client.put(
        "/api/v1/admin/stock",
        json={"variant_id": str(catalogue.variants[0].id), "total_quantity": 5},
    )

    assert response.status_code == 409
    assert "12" in response.json()["detail"]


def test_stock_may_be_set_to_exactly_what_is_committed(
    client: TestClient, db: Session, catalogue: Product
) -> None:
    inventory = catalogue.variants[0].inventory
    inventory.reserved_quantity = 7
    inventory.sold_quantity = 5
    db.flush()
    sign_in(client, db, UserRole.ADMIN)

    body = client.put(
        "/api/v1/admin/stock",
        json={"variant_id": str(catalogue.variants[0].id), "total_quantity": 12},
    ).json()

    assert body["available_quantity"] == 0


def test_setting_stock_on_a_variant_that_does_not_exist(client: TestClient, db: Session) -> None:
    sign_in(client, db, UserRole.ADMIN)

    response = client.put(
        "/api/v1/admin/stock",
        json={"variant_id": "00000000-0000-0000-0000-000000000000", "total_quantity": 5},
    )

    assert response.status_code == 404
