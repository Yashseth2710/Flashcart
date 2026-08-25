import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import TimestampedAt, UUIDPrimaryKey

if TYPE_CHECKING:
    from app.models.flash_sale import FlashSale
    from app.models.product import Product
    from app.models.user import User


class SavedProduct(UUIDPrimaryKey, TimestampedAt, Base):
    """Something a shopper wants to be told about.

    Saving is a marker rather than a claim: it holds no stock, survives sales
    coming and going, and can be made before a product is ever in one. The
    unique pair is what makes saving twice the same as saving once, so a second
    tap on the button is not an error.
    """

    __tablename__ = "saved_products"
    __table_args__ = (UniqueConstraint("user_id", "product_id", name="uq_saved_user_product"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), index=True, nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="saved_products")
    product: Mapped["Product"] = relationship()

    def __repr__(self) -> str:
        return f"<SavedProduct {self.user_id} {self.product_id}>"


class SaleReminder(UUIDPrimaryKey, TimestampedAt, Base):
    """A shopper asking to be shown a sale when they next come back.

    Nothing is sent anywhere. The reminder is read on arrival and turned into
    what is on the screen, which is why it needs no scheduler and no address to
    deliver to.
    """

    __tablename__ = "sale_reminders"
    __table_args__ = (UniqueConstraint("user_id", "flash_sale_id", name="uq_reminder_user_sale"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    flash_sale_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("flash_sales.id", ondelete="CASCADE"), index=True, nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="sale_reminders")
    flash_sale: Mapped["FlashSale"] = relationship()

    def __repr__(self) -> str:
        return f"<SaleReminder {self.user_id} {self.flash_sale_id}>"
