import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Enum, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import TimestampedAt, UUIDPrimaryKey
from app.models.enums import OrderStatus

if TYPE_CHECKING:
    from app.models.reservation import Reservation
    from app.models.user import User


class Order(UUIDPrimaryKey, TimestampedAt, Base):
    __tablename__ = "orders"
    __table_args__ = (
        CheckConstraint("subtotal >= 0", name="ck_orders_subtotal_not_negative"),
        CheckConstraint("total >= 0", name="ck_orders_total_not_negative"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    # One reservation can become at most one order; the unique constraint is what
    # stops a retried checkout from billing the same hold twice.
    reservation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("reservations.id", ondelete="SET NULL"), unique=True
    )
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, name="order_status"), default=OrderStatus.PAID, nullable=False
    )
    subtotal: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    total: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    user: Mapped["User"] = relationship(back_populates="orders")
    reservation: Mapped["Reservation | None"] = relationship(back_populates="order")
    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Order {self.id} {self.status.value}>"


class OrderItem(UUIDPrimaryKey, Base):
    """A line on an order.

    Name and price are copied rather than referenced so a past order still reads
    correctly after the catalogue is edited.
    """

    __tablename__ = "order_items"
    __table_args__ = (
        CheckConstraint("quantity >= 1", name="ck_order_items_quantity_at_least_one"),
        CheckConstraint("price_snapshot >= 0", name="ck_order_items_price_not_negative"),
    )

    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), index=True, nullable=False
    )
    variant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("product_variants.id", ondelete="SET NULL")
    )
    product_name_snapshot: Mapped[str] = mapped_column(String(320), nullable=False)
    price_snapshot: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)

    order: Mapped["Order"] = relationship(back_populates="items")

    def __repr__(self) -> str:
        return f"<OrderItem {self.product_name_snapshot} x{self.quantity}>"
