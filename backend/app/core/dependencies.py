import uuid
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import NotAuthenticated, NotPermitted
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models import User, UserRole
from app.repositories.user import UserRepository

DbSession = Annotated[Session, Depends(get_db)]


def get_current_user(request: Request, db: DbSession) -> User:
    """Reads the session cookie by its configured name, so renaming the cookie
    in settings does not require touching this signature."""
    token = request.cookies.get(get_settings().cookie_name)
    if not token:
        raise NotAuthenticated

    payload = decode_access_token(token)
    if payload is None:
        raise NotAuthenticated

    try:
        user_id = uuid.UUID(payload.get("sub", ""))
    except ValueError:
        raise NotAuthenticated from None

    # The account is re-read rather than trusted from the token, so a role change
    # or a deleted account takes effect on the next request.
    user = UserRepository(db).get_by_id(user_id)
    if user is None:
        raise NotAuthenticated
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_admin(user: CurrentUser) -> User:
    if user.role is not UserRole.ADMIN:
        raise NotPermitted
    return user


AdminUser = Annotated[User, Depends(require_admin)]
