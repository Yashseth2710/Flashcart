"""Turning dataset records into products, variants and stock."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.cli.import_catalogue import money, slugify, store, variant_sku
from app.models import Inventory, Product, ProductVariant


def unique_title() -> str:
    """Titles must not collide with a catalogue that was really imported."""
    return f"Test Item {uuid.uuid4().hex[:10]}"


def record(**overrides):
    base = {
        "title": unique_title(),
        "description": "A mascara.",
        "category": "beauty",
        "brand": "Essence",
        "price": 9.99,
        "stock": 99,
        "sku": f"TST-{uuid.uuid4().hex[:8].upper()}",
        "thumbnail": "https://example.com/mascara.png",
    }
    return {**base, **overrides}


def test_a_title_becomes_a_readable_slug() -> None:
    assert slugify("Essence Mascara Lash Princess") == "essence-mascara-lash-princess"


def test_accents_and_symbols_do_not_survive_a_slug() -> None:
    assert slugify("Café  Crème & Co.") == "cafe-creme-co"


def test_prices_keep_two_decimal_places() -> None:
    assert str(money(9.999)) == "10.00"
    assert str(money(9.99)) == "9.99"


def test_a_product_without_a_dataset_sku_still_gets_one() -> None:
    assert variant_sku({}, "bamboo-spatula") == "BAMBOO-SPATULA-STD"


def test_importing_creates_a_product_a_variant_and_stock(db: Session) -> None:
    """The dataset has no variants, so each product gets one to hang stock on."""
    incoming = record()
    added, updated = store(db, [incoming])

    assert (added, updated) == (1, 0)
    product = db.scalar(select(Product).where(Product.slug == slugify(incoming["title"])))
    assert product is not None
    assert product.brand == "Essence"
    assert product.image_url == "https://example.com/mascara.png"

    variant = db.scalar(select(ProductVariant).where(ProductVariant.product_id == product.id))
    assert variant is not None
    assert variant.name == "Standard"

    inventory = db.scalar(select(Inventory).where(Inventory.variant_id == variant.id))
    assert inventory is not None
    assert inventory.total_quantity == 99
    assert inventory.available_quantity == 99


def test_importing_the_same_product_twice_does_not_duplicate_it(db: Session) -> None:
    incoming = record()
    store(db, [incoming])
    added, updated = store(db, [{**incoming, "price": 12.50}])

    assert (added, updated) == (0, 1)
    matching = db.scalars(select(Product).where(Product.slug == slugify(incoming["title"]))).all()
    assert len(matching) == 1
    assert str(matching[0].base_price) == "12.50"


def test_a_repeat_import_never_drops_stock_below_what_is_committed(db: Session) -> None:
    """Re-importing must not invalidate holds and sales already on the books."""
    incoming = record(stock=99)
    store(db, [incoming])
    product = db.scalar(select(Product).where(Product.slug == slugify(incoming["title"])))
    variant = db.scalar(select(ProductVariant).where(ProductVariant.product_id == product.id))
    inventory = db.scalar(select(Inventory).where(Inventory.variant_id == variant.id))
    inventory.reserved_quantity = 5
    inventory.sold_quantity = 3
    db.flush()

    store(db, [{**incoming, "stock": 2}])

    assert inventory.total_quantity == 8
    assert inventory.available_quantity == 0


def test_two_products_sharing_a_sku_do_not_collide(db: Session) -> None:
    first, second = record(), record()
    shared = {"sku": "SHARED-SKU-001"}
    store(db, [{**first, **shared}, {**second, **shared}])

    slugs = [slugify(first["title"]), slugify(second["title"])]
    variants = db.scalars(
        select(ProductVariant)
        .join(Product, Product.id == ProductVariant.product_id)
        .where(Product.slug.in_(slugs))
    ).all()
    assert len({v.sku for v in variants}) == 2


def test_a_record_without_a_title_is_skipped(db: Session) -> None:
    added, updated = store(db, [record(title="  ")])

    assert (added, updated) == (0, 0)


def test_the_same_title_twice_in_one_batch_is_imported_once(db: Session) -> None:
    incoming = record()
    added, _ = store(db, [incoming, dict(incoming)])

    assert added == 1
