import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models import FlashSale, FlashSaleProduct, ProductVariant, Reservation
from app.models.enums import ReservationStatus


class ReservationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def lock_sale_product(self, sale_product_id: uuid.UUID) -> FlashSaleProduct | None:
        """Takes the row and holds it for the rest of the transaction.

        This is the single point where overselling is decided. Everyone reaching
        for the same item queues here, so each request reads counters that already
        include every hold placed before it rather than a snapshot taken before
        the queue formed. Postgres releases the row at commit or rollback.

        Only this one row is locked. Two sales, or two products in one sale, never
        wait on each other.
        """
        return self.db.scalar(
            select(FlashSaleProduct)
            .where(FlashSaleProduct.id == sale_product_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )

    def sale_for_product(self, sale_product_id: uuid.UUID) -> FlashSale | None:
        return self.db.scalar(
            select(FlashSale)
            .join(FlashSaleProduct, FlashSaleProduct.flash_sale_id == FlashSale.id)
            .where(FlashSaleProduct.id == sale_product_id)
        )

    def quantity_held_by(
        self, user_id: uuid.UUID, sale_product_id: uuid.UUID, *, now: datetime
    ) -> int:
        """How many units this person already has claim to on this item.

        Counts live holds and completed ones together: buying counts towards a
        per-person limit just as much as holding does, or the limit could be
        walked past one checkout at a time. Holds whose time has run out are
        excluded by the clock, not by their stored status.
        """
        total = self.db.scalar(
            select(func.coalesce(func.sum(Reservation.quantity), 0)).where(
                Reservation.user_id == user_id,
                Reservation.flash_sale_product_id == sale_product_id,
                Reservation.status.in_([ReservationStatus.ACTIVE, ReservationStatus.COMPLETED]),
                # An ACTIVE row past its time has no claim; a COMPLETED one always does.
                (Reservation.status == ReservationStatus.COMPLETED)
                | (Reservation.expires_at > now),
            )
        )
        return int(total or 0)

    def get(self, reservation_id: uuid.UUID) -> Reservation | None:
        return self.db.get(Reservation, reservation_id)

    def _described(self):
        return select(Reservation).options(
            selectinload(Reservation.sale_product)
            .selectinload(FlashSaleProduct.variant)
            .selectinload(ProductVariant.product),
            selectinload(Reservation.sale_product).selectinload(FlashSaleProduct.flash_sale),
        )

    def describe(self, reservation_id: uuid.UUID) -> Reservation | None:
        return self.db.scalar(
            self._described()
            .where(Reservation.id == reservation_id)
            .execution_options(populate_existing=True)
        )

    def for_user(self, user_id: uuid.UUID) -> list[Reservation]:
        """Newest first, which is the order someone reads their own holds in."""
        return list(
            self.db.scalars(
                self._described()
                .where(Reservation.user_id == user_id)
                .order_by(Reservation.created_at.desc())
                .execution_options(populate_existing=True)
            ).all()
        )

    def expired_still_holding(self, now: datetime) -> list[Reservation]:
        """ACTIVE rows the clock has passed. What the sweep tidies up."""
        return list(
            self.db.scalars(
                select(Reservation)
                .where(
                    Reservation.status == ReservationStatus.ACTIVE,
                    Reservation.expires_at <= now,
                )
                .with_for_update(skip_locked=True)
            ).all()
        )
