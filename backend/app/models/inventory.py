import uuid
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import UUIDPrimaryKey

if TYPE_CHECKING:
    from app.models.product import ProductVariant


class Inventory(UUIDPrimaryKey, Base):
    """Warehouse stock for one variant.

    The constraints below are the real guarantee against overselling. Application
    code can be wrong; a row that breaks these cannot be written at all.
    """

    __tablename__ = "inventory"
    __table_args__ = (
        CheckConstraint("total_quantity >= 0", name="ck_inventory_total_not_negative"),
        CheckConstraint("reserved_quantity >= 0", name="ck_inventory_reserved_not_negative"),
        CheckConstraint("sold_quantity >= 0", name="ck_inventory_sold_not_negative"),
        CheckConstraint(
            "reserved_quantity + sold_quantity <= total_quantity",
            name="ck_inventory_committed_within_total",
        ),
    )

    variant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("product_variants.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    total_quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reserved_quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sold_quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    variant: Mapped["ProductVariant"] = relationship(back_populates="inventory")

    @property
    def available_quantity(self) -> int:
        return self.total_quantity - self.reserved_quantity - self.sold_quantity

    def __repr__(self) -> str:
        return (
            f"<Inventory variant={self.variant_id} "
            f"total={self.total_quantity} reserved={self.reserved_quantity} "
            f"sold={self.sold_quantity}>"
        )
