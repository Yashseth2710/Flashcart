import uuid

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models import Inventory, Product, ProductVariant


class ProductRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _visible(self, *, include_inactive: bool) -> Select[tuple[Product]]:
        statement = select(Product)
        if not include_inactive:
            statement = statement.where(Product.is_active.is_(True))
        return statement

    def search(
        self,
        *,
        term: str | None = None,
        category: str | None = None,
        limit: int = 24,
        offset: int = 0,
        include_inactive: bool = False,
        newest_first: bool = False,
    ) -> tuple[list[Product], int]:
        statement = self._visible(include_inactive=include_inactive)

        if term:
            pattern = f"%{term.strip()}%"
            statement = statement.where(
                or_(Product.name.ilike(pattern), Product.brand.ilike(pattern))
            )
        if category:
            statement = statement.where(Product.category == category)

        total = self.db.scalar(select(func.count()).select_from(statement.subquery()))
        # Shoppers read an alphabetical shelf; someone managing the shop wants to
        # see what they just added, which is the newest thing.
        order = Product.created_at.desc() if newest_first else Product.name
        items = list(self.db.scalars(statement.order_by(order).limit(limit).offset(offset)).all())
        return items, total or 0

    def get_by_slug(self, slug: str, *, include_inactive: bool = False) -> Product | None:
        statement = self._visible(include_inactive=include_inactive).where(Product.slug == slug)
        return self.db.scalar(
            statement.options(selectinload(Product.variants).selectinload(ProductVariant.inventory))
        )

    def get_by_id(self, product_id: uuid.UUID) -> Product | None:
        return self.db.get(Product, product_id)

    def categories(self) -> list[str]:
        statement = (
            select(Product.category)
            .where(Product.is_active.is_(True), Product.category.is_not(None))
            .distinct()
            .order_by(Product.category)
        )
        return [row for row in self.db.scalars(statement).all() if row]

    def slug_exists(self, slug: str) -> bool:
        return bool(self.db.scalar(select(Product.id).where(Product.slug == slug)))

    def add(self, product: Product) -> Product:
        self.db.add(product)
        self.db.flush()
        return product


class InventoryRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def for_variant(self, variant_id: uuid.UUID) -> Inventory | None:
        return self.db.scalar(select(Inventory).where(Inventory.variant_id == variant_id))

    def get_variant(self, variant_id: uuid.UUID) -> ProductVariant | None:
        return self.db.get(ProductVariant, variant_id)

    def levels_for_product(self, product_id: uuid.UUID) -> list[tuple[ProductVariant, Inventory]]:
        statement = (
            select(ProductVariant, Inventory)
            .join(Inventory, Inventory.variant_id == ProductVariant.id)
            .where(ProductVariant.product_id == product_id)
            .order_by(ProductVariant.sku)
        )
        return [(variant, inventory) for variant, inventory in self.db.execute(statement)]
