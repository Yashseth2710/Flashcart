import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import (
    ProductNotFound,
    StockBelowCommitted,
    VariantNotFound,
)
from app.core.text import slugify
from app.models import Inventory, Product, ProductVariant
from app.repositories.catalogue import InventoryRepository, ProductRepository
from app.schemas.catalogue import ProductUpdate, ProductWrite


class CatalogueService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.products = ProductRepository(db)
        self.inventory = InventoryRepository(db)

    def browse(
        self,
        *,
        term: str | None,
        category: str | None,
        limit: int,
        offset: int,
        include_inactive: bool = False,
        newest_first: bool = False,
    ) -> tuple[list[Product], int]:
        return self.products.search(
            term=term,
            category=category,
            limit=limit,
            offset=offset,
            include_inactive=include_inactive,
            newest_first=newest_first,
        )

    def read(self, slug: str, *, include_inactive: bool = False) -> Product:
        product = self.products.get_by_slug(slug, include_inactive=include_inactive)
        if product is None:
            raise ProductNotFound
        return product

    def unique_slug(self, name: str) -> str:
        """A slug nothing else is using, so two products can share a name."""
        base = slugify(name) or "product"
        candidate = base
        for suffix in range(2, 200):
            if not self.products.slug_exists(candidate):
                return candidate
            candidate = f"{base}-{suffix}"
        raise ProductNotFound

    def create(self, payload: ProductWrite) -> Product:
        """A new product comes with one variant and an empty stock row, because
        stock hangs off a variant and a product with neither cannot be sold."""
        product = Product(**payload.model_dump(), slug=self.unique_slug(payload.name))
        self.products.add(product)

        variant = ProductVariant(
            product_id=product.id,
            sku=f"{product.slug[:40].upper()}-STD",
            name="Standard",
            price=payload.base_price,
            attributes={},
        )
        self.db.add(variant)
        self.db.flush()

        self.db.add(Inventory(variant_id=variant.id, total_quantity=0))
        self.db.commit()
        return self.read(product.slug, include_inactive=True)

    def update(self, product_id: uuid.UUID, payload: ProductUpdate) -> Product:
        product = self.products.get_by_id(product_id)
        if product is None:
            raise ProductNotFound

        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(product, field, value)
        self.db.commit()
        return self.read(product.slug, include_inactive=True)

    def set_stock(
        self, variant_id: uuid.UUID, total_quantity: int
    ) -> tuple[ProductVariant, Inventory]:
        variant = self.inventory.get_variant(variant_id)
        if variant is None:
            raise VariantNotFound

        inventory = self.inventory.for_variant(variant_id)
        if inventory is None:
            inventory = Inventory(variant_id=variant_id, total_quantity=0)
            self.db.add(inventory)
            self.db.flush()

        committed = inventory.reserved_quantity + inventory.sold_quantity
        if total_quantity < committed:
            raise StockBelowCommitted(committed)

        inventory.total_quantity = total_quantity
        self.db.commit()
        return variant, inventory
