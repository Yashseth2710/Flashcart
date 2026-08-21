import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Index, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import TimestampedAt, UUIDPrimaryKey
from app.models.enums import ReservationStatus

if TYPE_CHECKING:
    from app.models.flash_sale import FlashSaleProduct
    from app.models.order import Order
    from app.models.user import User


class Reservation(UUIDPrimaryKey, TimestampedAt, Base):
    """A temporary hold on sale stock.

    A hold is only real while it is ACTIVE *and* the clock has not passed
    expires_at. Both halves are checked on every read; a status left stale by a
    missed sweep never grants a claim on stock.
    """

    __tablename__ = "reservations"
    __table_args__ = (
        CheckConstraint("quantity >= 1", name="ck_reservations_quantity_at_least_one"),
        CheckConstraint("expires_at > created_at", name="ck_reservations_expires_after_creation"),
        Index("ix_reservations_user_status", "user_id", "status"),
        Index("ix_reservations_sweep", "status", "expires_at"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    flash_sale_product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("flash_sale_products.id", ondelete="CASCADE"), index=True, nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[ReservationStatus] = mapped_column(
        Enum(ReservationStatus, name="reservation_status"),
        default=ReservationStatus.ACTIVE,
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    user: Mapped["User"] = relationship(back_populates="reservations")
    sale_product: Mapped["FlashSaleProduct"] = relationship(back_populates="reservations")
    order: Mapped["Order | None"] = relationship(back_populates="reservation", uselist=False)

    def is_holding_stock(self, now: datetime) -> bool:
        """Whether this hold still has a claim on stock.

        A column default only lands at insert time, so an unsaved reservation
        reads as ACTIVE here rather than as having no status at all.
        """
        status = self.status or ReservationStatus.ACTIVE
        return status is ReservationStatus.ACTIVE and self.expires_at > now

    def __repr__(self) -> str:
        return f"<Reservation {self.id} {self.status.value}>"
