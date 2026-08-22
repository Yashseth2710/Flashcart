from typing import TYPE_CHECKING

from sqlalchemy import Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import Timestamped, UUIDPrimaryKey
from app.models.enums import UserRole

if TYPE_CHECKING:
    from app.models.order import Order
    from app.models.reservation import Reservation


class User(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "users"

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"), default=UserRole.CUSTOMER, nullable=False
    )

    # The database already cascades reservations when an account goes. Saying so
    # here stops the session trying to orphan them by nulling user_id first.
    reservations: Mapped[list["Reservation"]] = relationship(
        back_populates="user", passive_deletes=True
    )
    orders: Mapped[list["Order"]] = relationship(back_populates="user")

    def __repr__(self) -> str:
        return f"<User {self.email}>"
