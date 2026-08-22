import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import TimestampedAt, UUIDPrimaryKey

if TYPE_CHECKING:
    from app.models.product import ProductVariant
    from app.models.reservation import Reservation
    from app.models.user import User


class FlashSale(UUIDPrimaryKey, TimestampedAt, Base):
    """A selling window. Status is derived from the clock, never stored."""

    __tablename__ = "flash_sales"
    __table_args__ = (
        CheckConstraint("end_time > start_time", name="ck_flash_sales_ends_after_start"),
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    start_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True, nullable=False
    )
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )

    creator: Mapped["User | None"] = relationship()
    sale_products: Mapped[list["FlashSaleProduct"]] = relationship(
        back_populates="flash_sale", cascade="all, delete-orphan"
    )

    def status_at(self, now: datetime) -> str:
        """Read from the clock rather than stored, so it can never go stale."""
        if now < self.start_time:
            return "UPCOMING"
        if now < self.end_time:
            return "ACTIVE"
        return "ENDED"

    def is_running_at(self, now: datetime) -> bool:
        return self.start_time <= now < self.end_time

    def __repr__(self) -> str:
        return f"<FlashSale {self.name}>"


class FlashSaleProduct(UUIDPrimaryKey, TimestampedAt, Base):
    """Stock carved out of warehouse inventory for one sale.

    Reservations lock this row rather than the warehouse inventory row, so a sale
    holds its own ring-fenced pool and two concurrent sales never block each other.
    """

    __tablename__ = "flash_sale_products"
    __table_args__ = (
        UniqueConstraint("flash_sale_id", "variant_id", name="uq_sale_variant"),
        CheckConstraint("sale_price >= 0", name="ck_sale_products_price_positive"),
        CheckConstraint("allocated_quantity >= 0", name="ck_sale_products_allocation_not_negative"),
        CheckConstraint("reserved_quantity >= 0", name="ck_sale_products_reserved_not_negative"),
        CheckConstraint("sold_quantity >= 0", name="ck_sale_products_sold_not_negative"),
        CheckConstraint("max_per_user >= 1", name="ck_sale_products_limit_at_least_one"),
        CheckConstraint(
            "reserved_quantity + sold_quantity <= allocated_quantity",
            name="ck_sale_products_committed_within_allocation",
        ),
    )

    flash_sale_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("flash_sales.id", ondelete="CASCADE"), index=True, nullable=False
    )
    variant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("product_variants.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    sale_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    allocated_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    reserved_quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sold_quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_per_user: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    flash_sale: Mapped["FlashSale"] = relationship(back_populates="sale_products")
    variant: Mapped["ProductVariant"] = relationship()
    reservations: Mapped[list["Reservation"]] = relationship(back_populates="sale_product")

    @property
    def available_quantity(self) -> int:
        return self.allocated_quantity - self.reserved_quantity - self.sold_quantity

    def __repr__(self) -> str:
        return f"<FlashSaleProduct sale={self.flash_sale_id} variant={self.variant_id}>"
