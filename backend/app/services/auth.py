from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import (
    ConfirmationDoesNotMatch,
    EmailAlreadyRegistered,
    InvalidCredentials,
    OrdersMustBeKept,
)
from app.core.security import (
    hash_password,
    needs_rehash,
    verify_password,
    waste_a_verification,
)
from app.models import Order, Reservation, ReservationStatus, User, UserRole
from app.repositories.user import UserRepository


def normalise_email(email: str) -> str:
    return email.strip().lower()


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.users = UserRepository(db)

    def register(self, *, name: str, email: str, password: str) -> User:
        email = normalise_email(email)
        if self.users.get_by_email(email):
            raise EmailAlreadyRegistered

        user = self.users.create(
            name=name.strip(),
            email=email,
            password_hash=hash_password(password),
            role=UserRole.CUSTOMER,
        )
        try:
            self.db.commit()
        except IntegrityError:
            # Two registrations for the same address can pass the check above
            # simultaneously; the unique index is what actually decides.
            self.db.rollback()
            raise EmailAlreadyRegistered from None
        return user

    def authenticate(self, *, email: str, password: str) -> User:
        user = self.users.get_by_email(normalise_email(email))
        if user is None:
            waste_a_verification()
            raise InvalidCredentials
        if not verify_password(password, user.password_hash):
            raise InvalidCredentials

        if needs_rehash(user.password_hash):
            user.password_hash = hash_password(password)
            self.db.commit()
        return user

    def rename(self, user: User, name: str) -> User:
        user.name = name.strip()
        self.db.commit()
        return user

    def change_password(self, user: User, *, current: str, replacement: str) -> None:
        if not verify_password(current, user.password_hash):
            raise InvalidCredentials
        user.password_hash = hash_password(replacement)
        self.db.commit()

    def close_account(self, user: User, *, confirmation: str) -> None:
        """Deletes an account, provided nothing was ever bought with it.

        Orders are a record of money changing hands, so an account attached to
        any is kept. Live holds are handed back to their sale first, otherwise
        that stock would sit unavailable until it expired.
        """
        if normalise_email(confirmation) != user.email:
            raise ConfirmationDoesNotMatch

        orders = self.db.scalar(
            select(func.count()).select_from(Order).where(Order.user_id == user.id)
        )
        if orders:
            raise OrdersMustBeKept(orders)

        # The reservation rows go with the account. What has to happen first is
        # handing their stock back, or it would sit unavailable until it expired.
        now = datetime.now(UTC)
        holds = self.db.scalars(
            select(Reservation).where(
                Reservation.user_id == user.id,
                Reservation.status == ReservationStatus.ACTIVE,
            )
        ).all()
        for hold in holds:
            if hold.is_holding_stock(now):
                hold.sale_product.reserved_quantity -= hold.quantity

        self.db.flush()
        self.db.delete(user)
        self.db.commit()
