import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    FlashSale,
    FlashSaleProduct,
    Product,
    ProductVariant,
    SaleReminder,
    SavedProduct,
)


class SavedRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    # Saved products

    def saved_for(self, user_id: uuid.UUID) -> list[SavedProduct]:
        """Newest first, which is the order someone reads their own list in."""
        return list(
            self.db.scalars(
                select(SavedProduct)
                .options(selectinload(SavedProduct.product))
                .where(SavedProduct.user_id == user_id)
                .order_by(SavedProduct.created_at.desc())
                .execution_options(populate_existing=True)
            ).all()
        )

    def saved_one(self, user_id: uuid.UUID, product_id: uuid.UUID) -> SavedProduct | None:
        return self.db.scalar(
            select(SavedProduct).where(
                SavedProduct.user_id == user_id, SavedProduct.product_id == product_id
            )
        )

    def saved_product_ids(self, user_id: uuid.UUID) -> set[uuid.UUID]:
        return set(
            self.db.scalars(
                select(SavedProduct.product_id).where(SavedProduct.user_id == user_id)
            ).all()
        )

    def count_saved(self, user_id: uuid.UUID) -> int:
        return (
            self.db.scalar(
                select(func.count())
                .select_from(SavedProduct)
                .where(SavedProduct.user_id == user_id)
            )
            or 0
        )

    def product(self, product_id: uuid.UUID) -> Product | None:
        return self.db.get(Product, product_id)

    def live_sale_entries(self, product_ids: set[uuid.UUID], *, now: datetime) -> dict:
        """Where each product currently sits in a sale that has not finished.

        A product can appear in several sales over time; only one that is still
        to come or running is worth showing, and the soonest of those is the one
        a shopper means. Finished sales are left out entirely.
        """
        if not product_ids:
            return {}

        rows = self.db.execute(
            select(FlashSaleProduct, FlashSale, ProductVariant.product_id)
            .join(FlashSale, FlashSale.id == FlashSaleProduct.flash_sale_id)
            .join(ProductVariant, ProductVariant.id == FlashSaleProduct.variant_id)
            .where(
                ProductVariant.product_id.in_(product_ids),
                FlashSale.end_time > now,
            )
            .order_by(FlashSale.start_time)
        ).all()

        found: dict = {}
        for entry, sale, product_id in rows:
            # Ordered by start time, so the first seen is the soonest.
            found.setdefault(product_id, (entry, sale))
        return found

    # Reminders

    def reminders_for(self, user_id: uuid.UUID) -> list[SaleReminder]:
        return list(
            self.db.scalars(
                select(SaleReminder)
                .options(
                    selectinload(SaleReminder.flash_sale).selectinload(FlashSale.sale_products)
                )
                .where(SaleReminder.user_id == user_id)
                .execution_options(populate_existing=True)
            ).all()
        )

    def reminder_one(self, user_id: uuid.UUID, sale_id: uuid.UUID) -> SaleReminder | None:
        return self.db.scalar(
            select(SaleReminder).where(
                SaleReminder.user_id == user_id, SaleReminder.flash_sale_id == sale_id
            )
        )

    def reminded_sale_ids(self, user_id: uuid.UUID) -> set[uuid.UUID]:
        return set(
            self.db.scalars(
                select(SaleReminder.flash_sale_id).where(SaleReminder.user_id == user_id)
            ).all()
        )

    def count_reminders(self, user_id: uuid.UUID, *, unfinished_after: datetime) -> int:
        """Only sales still to come or running; a past one is not a reminder."""
        return (
            self.db.scalar(
                select(func.count())
                .select_from(SaleReminder)
                .join(FlashSale, FlashSale.id == SaleReminder.flash_sale_id)
                .where(SaleReminder.user_id == user_id, FlashSale.end_time > unfinished_after)
            )
            or 0
        )

    def sale(self, sale_id: uuid.UUID) -> FlashSale | None:
        return self.db.scalar(
            select(FlashSale)
            .options(selectinload(FlashSale.sale_products))
            .where(FlashSale.id == sale_id)
        )

    def saved_products_in_sale(self, user_id: uuid.UUID, sale_id: uuid.UUID) -> int:
        """How many of this person's saved products the sale actually carries."""
        return (
            self.db.scalar(
                select(func.count(func.distinct(SavedProduct.product_id)))
                .select_from(SavedProduct)
                .join(ProductVariant, ProductVariant.product_id == SavedProduct.product_id)
                .join(FlashSaleProduct, FlashSaleProduct.variant_id == ProductVariant.id)
                .where(
                    SavedProduct.user_id == user_id,
                    FlashSaleProduct.flash_sale_id == sale_id,
                )
            )
            or 0
        )
