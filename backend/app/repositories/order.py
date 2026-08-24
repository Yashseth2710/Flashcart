import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import IdempotencyKey, Order, OrderItem, Product, ProductVariant
from app.models.enums import IdempotencyStatus


class OrderRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _described(self):
        return select(Order).options(
            selectinload(Order.items),
            selectinload(Order.reservation),
        )

    def get(self, order_id: uuid.UUID) -> Order | None:
        return self.db.scalar(
            self._described().where(Order.id == order_id).execution_options(populate_existing=True)
        )

    def for_user(self, user_id: uuid.UUID) -> list[Order]:
        """Newest first, the order someone reads their own purchases in."""
        return list(
            self.db.scalars(
                self._described()
                .where(Order.user_id == user_id)
                .order_by(Order.created_at.desc())
                .execution_options(populate_existing=True)
            ).all()
        )

    def for_reservation(self, reservation_id: uuid.UUID) -> Order | None:
        return self.db.scalar(self._described().where(Order.reservation_id == reservation_id))

    def product_for_variant(self, variant_id: uuid.UUID) -> Product | None:
        return self.db.scalar(
            select(Product)
            .join(ProductVariant, ProductVariant.product_id == Product.id)
            .where(ProductVariant.id == variant_id)
        )

    def lines_of(self, order_id: uuid.UUID) -> list[OrderItem]:
        return list(self.db.scalars(select(OrderItem).where(OrderItem.order_id == order_id)).all())

    # Idempotency

    def claim_key(
        self, *, user_id: uuid.UUID, key: str, request_hash: str, expires_at: datetime
    ) -> IdempotencyKey:
        """Records that this key is being worked on. The unique index on
        (user_id, key) is what makes a second claim fail rather than proceed."""
        claim = IdempotencyKey(
            user_id=user_id,
            key=key,
            request_hash=request_hash,
            status=IdempotencyStatus.IN_PROGRESS,
            expires_at=expires_at,
        )
        self.db.add(claim)
        self.db.flush()
        return claim

    def find_key(self, *, user_id: uuid.UUID, key: str) -> IdempotencyKey | None:
        return self.db.scalar(
            select(IdempotencyKey)
            .where(IdempotencyKey.user_id == user_id, IdempotencyKey.key == key)
            .execution_options(populate_existing=True)
        )
