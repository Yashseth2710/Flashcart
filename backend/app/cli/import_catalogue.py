"""Fill the catalogue from a public product dataset.

Run this once to avoid typing in hundreds of products by hand:

    python -m app.cli.import_catalogue --limit 100

Nothing at runtime talks to the dataset. Once the rows are here, this database
is the only place FlashCart reads products from.

Re-running is safe: products are matched on their slug and updated in place
rather than duplicated.
"""

import argparse
import sys
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.text import slugify
from app.db.session import get_session_factory
from app.models import Inventory, Product, ProductVariant

SOURCE = "https://dummyjson.com/products"
PAGE_SIZE = 100


def money(value: float) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def fetch(limit: int) -> list[dict[str, Any]]:
    """Pages through the dataset until it has `limit` products or runs out."""
    collected: list[dict[str, Any]] = []
    with httpx.Client(timeout=30, follow_redirects=True) as client:
        while len(collected) < limit:
            response = client.get(
                SOURCE,
                params={
                    "limit": min(PAGE_SIZE, limit - len(collected)),
                    "skip": len(collected),
                },
            )
            response.raise_for_status()
            body = response.json()
            page = body.get("products", [])
            if not page:
                break
            collected.extend(page)
            if len(collected) >= body.get("total", 0):
                break
    return collected[:limit]


def variant_sku(record: dict[str, Any], slug: str) -> str:
    """The dataset's own SKU where there is one, otherwise a stable fallback."""
    supplied = (record.get("sku") or "").strip()
    return supplied or f"{slug[:40].upper()}-STD"


def is_taken(db: Session, candidate: str, taken: set[str]) -> bool:
    return candidate in taken or bool(
        db.scalar(select(ProductVariant.id).where(ProductVariant.sku == candidate))
    )


def free_sku(db: Session, record: dict[str, Any], slug: str, taken: set[str]) -> str:
    """A SKU nothing else is using.

    The dataset repeats SKUs across products, and the catalogue may already hold
    one from an earlier import, so the slug is appended until the code is free.
    """
    candidate = variant_sku(record, slug)
    if not is_taken(db, candidate, taken):
        return candidate

    with_slug = f"{candidate[:40]}-{slug[:12].upper()}"
    if not is_taken(db, with_slug, taken):
        return with_slug

    for suffix in range(2, 100):
        numbered = f"{with_slug[:50]}-{suffix}"
        if not is_taken(db, numbered, taken):
            return numbered

    raise RuntimeError(f"Could not find a free SKU for {slug}.")


def store(db: Session, records: list[dict[str, Any]]) -> tuple[int, int]:
    """Writes products, one variant each, and an inventory row for that variant.

    The dataset has no variants, but stock hangs off a variant in this schema,
    so each product gets a single standard one.
    """
    added = updated = 0
    seen_slugs: set[str] = set()
    seen_skus: set[str] = set()

    for record in records:
        title = (record.get("title") or "").strip()
        if not title:
            continue

        slug = slugify(title)
        if not slug or slug in seen_slugs:
            continue
        seen_slugs.add(slug)

        price = money(record.get("price") or 0)
        product = db.scalar(select(Product).where(Product.slug == slug))

        if product is None:
            product = Product(slug=slug)
            db.add(product)
            added += 1
        else:
            updated += 1

        product.name = title[:200]
        product.description = (record.get("description") or "").strip() or None
        product.category = (record.get("category") or "").strip()[:80] or None
        product.brand = (record.get("brand") or "").strip()[:120] or None
        product.image_url = (record.get("thumbnail") or "").strip()[:500] or None
        product.base_price = price
        product.is_active = True
        db.flush()

        sku = variant_sku(record, slug)
        if sku in seen_skus:
            sku = f"{sku}-{slug[:8].upper()}"
        seen_skus.add(sku)

        variant = db.scalar(select(ProductVariant).where(ProductVariant.product_id == product.id))
        if variant is None:
            variant = ProductVariant(product_id=product.id, sku=sku)
            db.add(variant)
        variant.name = "Standard"
        variant.price = price
        variant.attributes = {}
        db.flush()

        inventory = db.scalar(select(Inventory).where(Inventory.variant_id == variant.id))
        stock = max(0, int(record.get("stock") or 0))
        if inventory is None:
            db.add(Inventory(variant_id=variant.id, total_quantity=stock))
        else:
            # Never drop the total below what is already spoken for.
            inventory.total_quantity = max(
                stock, inventory.reserved_quantity + inventory.sold_quantity
            )
        db.flush()

    return added, updated


def main() -> int:
    parser = argparse.ArgumentParser(description="Fill the catalogue from a public dataset.")
    parser.add_argument("--limit", type=int, default=100, help="how many products to import")
    args = parser.parse_args()

    if args.limit < 1:
        print("--limit must be at least 1.", file=sys.stderr)
        return 1

    print(f"Fetching up to {args.limit} products...")
    try:
        records = fetch(args.limit)
    except httpx.HTTPError as error:
        print(f"Could not reach the dataset: {error}", file=sys.stderr)
        return 1

    print(f"Fetched {len(records)}. Writing to the database...")
    session = get_session_factory()()
    try:
        added, updated = store(session, records)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    print(f"Added {added}, updated {updated}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
