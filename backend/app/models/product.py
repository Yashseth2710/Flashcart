import uuid
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import Timestamped, TimestampedAt, UUIDPrimaryKey

if TYPE_CHECKING:
    from app.models.inventory import Inventory


class Product(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "products"
    __table_args__ = (CheckConstraint("base_price >= 0", name="ck_products_base_price_positive"),)

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(200), unique=True, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(String(80), index=True)
    base_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    variants: Mapped[list["ProductVariant"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Product {self.slug}>"


class ProductVariant(UUIDPrimaryKey, TimestampedAt, Base):
    __tablename__ = "product_variants"
    __table_args__ = (CheckConstraint("price >= 0", name="ck_variants_price_positive"),)

    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), index=True, nullable=False
    )
    sku: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    attributes: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    product: Mapped["Product"] = relationship(back_populates="variants")
    inventory: Mapped["Inventory"] = relationship(
        back_populates="variant", uselist=False, cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<ProductVariant {self.sku}>"
