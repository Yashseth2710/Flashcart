from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import EmailAlreadyRegistered, InvalidCredentials
from app.core.security import (
    hash_password,
    needs_rehash,
    verify_password,
    waste_a_verification,
)
from app.models import User, UserRole
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
