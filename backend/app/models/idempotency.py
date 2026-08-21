import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import TimestampedAt, UUIDPrimaryKey
from app.models.enums import IdempotencyStatus


class IdempotencyKey(UUIDPrimaryKey, TimestampedAt, Base):
    """A record of work already done for a client-supplied key.

    The request hash is stored alongside so that reusing a key with different
    parameters is refused rather than silently returning the earlier result.
    """

    __tablename__ = "idempotency_keys"
    __table_args__ = (UniqueConstraint("user_id", "key", name="uq_idempotency_user_key"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    key: Mapped[str] = mapped_column(String(255), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[IdempotencyStatus] = mapped_column(
        Enum(IdempotencyStatus, name="idempotency_status"),
        default=IdempotencyStatus.IN_PROGRESS,
        nullable=False,
    )
    response_reference: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    def __repr__(self) -> str:
        return f"<IdempotencyKey {self.key} {self.status.value}>"
