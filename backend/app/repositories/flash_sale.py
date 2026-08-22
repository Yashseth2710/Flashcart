import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import FlashSale, FlashSaleProduct, Inventory, Product, ProductVariant


class FlashSaleRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _with_items(self):
        return select(FlashSale).options(
            selectinload(FlashSale.sale_products)
            .selectinload(FlashSaleProduct.variant)
            .selectinload(ProductVariant.product)
        )

    def get(self, sale_id: uuid.UUID) -> FlashSale | None:
        """Reloads the sale and its items.

        Without populate_existing the session hands back the copy it already
        holds, so a sale read straight after an item was added still looks empty.
        """
        return self.db.scalar(
            self._with_items()
            .where(FlashSale.id == sale_id)
            .execution_options(populate_existing=True)
        )

    def listing(self, *, ended_before: datetime | None = None) -> list[FlashSale]:
        """Sales in the order people care about: what is on now, then what is next."""
        statement = self._with_items()
        if ended_before is not None:
            statement = statement.where(FlashSale.end_time > ended_before)
        return list(self.db.scalars(statement.order_by(FlashSale.start_time)).all())

    def all_sales(self) -> list[FlashSale]:
        return list(self.db.scalars(self._with_items().order_by(FlashSale.start_time.desc())).all())

    def add(self, sale: FlashSale) -> FlashSale:
        self.db.add(sale)
        self.db.flush()
        return sale

    def item(self, item_id: uuid.UUID) -> FlashSaleProduct | None:
        return self.db.get(FlashSaleProduct, item_id)

    def item_for_variant(
        self, sale_id: uuid.UUID, variant_id: uuid.UUID
    ) -> FlashSaleProduct | None:
        return self.db.scalar(
            select(FlashSaleProduct).where(
                FlashSaleProduct.flash_sale_id == sale_id,
                FlashSaleProduct.variant_id == variant_id,
            )
        )

    def variant_with_stock(self, variant_id: uuid.UUID) -> tuple[ProductVariant, Inventory] | None:
        row = self.db.execute(
            select(ProductVariant, Inventory)
            .join(Inventory, Inventory.variant_id == ProductVariant.id)
            .where(ProductVariant.id == variant_id)
        ).first()
        return (row[0], row[1]) if row else None

    def product_for_variant(self, variant_id: uuid.UUID) -> Product | None:
        return self.db.scalar(
            select(Product)
            .join(ProductVariant, ProductVariant.product_id == Product.id)
            .where(ProductVariant.id == variant_id)
        )
