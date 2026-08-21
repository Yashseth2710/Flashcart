import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User, UserRole


class UserRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, user_id: uuid.UUID) -> User | None:
        return self.db.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        return self.db.scalar(select(User).where(User.email == email))

    def create(self, *, name: str, email: str, password_hash: str, role: UserRole) -> User:
        user = User(name=name, email=email, password_hash=password_hash, role=role)
        self.db.add(user)
        self.db.flush()
        return user
