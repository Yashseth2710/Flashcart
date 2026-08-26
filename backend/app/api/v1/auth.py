from fastapi import APIRouter, Response, status

from app.core.config import get_settings
from app.core.dependencies import CurrentUser, DbSession
from app.core.limits import LimitLogins, LimitRegistrations
from app.core.security import create_access_token
from app.models import User
from app.schemas.auth import (
    AccountDeletion,
    LoginRequest,
    PasswordChange,
    ProfileUpdate,
    RegistrationRequest,
    UserProfile,
)
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


def _start_session(response: Response, user: User) -> None:
    """Sets the session cookie.

    The token is httpOnly so page scripts cannot read it, which keeps a cross-site
    scripting bug from turning into a stolen account.
    """
    settings = get_settings()
    response.set_cookie(
        key=settings.cookie_name,
        value=create_access_token(str(user.id), user.role.value),
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=settings.access_token_minutes * 60,
        path="/",
    )


@router.post(
    "/register",
    response_model=UserProfile,
    status_code=status.HTTP_201_CREATED,
    dependencies=[LimitRegistrations],
)
def register(payload: RegistrationRequest, response: Response, db: DbSession) -> User:
    user = AuthService(db).register(
        name=payload.name, email=payload.email, password=payload.password
    )
    _start_session(response, user)
    return user


@router.post("/login", response_model=UserProfile, dependencies=[LimitLogins])
def login(payload: LoginRequest, response: Response, db: DbSession) -> User:
    user = AuthService(db).authenticate(email=payload.email, password=payload.password)
    _start_session(response, user)
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> None:
    response.delete_cookie(get_settings().cookie_name, path="/")


@router.get("/me", response_model=UserProfile)
def read_current_user(user: CurrentUser) -> User:
    return user


@router.patch("/me", response_model=UserProfile)
def rename_account(payload: ProfileUpdate, user: CurrentUser, db: DbSession) -> User:
    return AuthService(db).rename(user, payload.name)


@router.post("/me/password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(payload: PasswordChange, user: CurrentUser, db: DbSession) -> None:
    AuthService(db).change_password(
        user, current=payload.current_password, replacement=payload.new_password
    )


@router.post("/me/delete", status_code=status.HTTP_204_NO_CONTENT)
def close_account(
    payload: AccountDeletion, user: CurrentUser, db: DbSession, response: Response
) -> None:
    """A POST rather than a DELETE, because it carries a body confirming intent."""
    AuthService(db).close_account(user, confirmation=payload.email)
    response.delete_cookie(get_settings().cookie_name, path="/")
