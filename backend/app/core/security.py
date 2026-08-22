from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

from app.core.config import get_settings

_hasher = PasswordHasher()

ALGORITHM = "HS256"

# Verified when no account matches, so answering an unknown address costs the
# same as answering a known one and cannot be told apart by timing.
_DUMMY_HASH = _hasher.hash("no-account-with-this-address")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        _hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False
    return True


def waste_a_verification() -> None:
    """Spend the same work as a real check, to keep timing uniform."""
    verify_password("irrelevant", _DUMMY_HASH)


def needs_rehash(password_hash: str) -> bool:
    """True when a stored hash predates the current cost settings."""
    return _hasher.check_needs_rehash(password_hash)


def create_access_token(subject: str, role: str) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": subject,
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any] | None:
    """Returns the payload, or None when the token is expired or not ours."""
    try:
        return jwt.decode(token, get_settings().jwt_secret, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return None
