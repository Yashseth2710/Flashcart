"""What the two kinds of account are allowed to reach."""

from fastapi import APIRouter
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.dependencies import AdminUser, CurrentUser
from app.core.security import create_access_token
from app.main import app
from app.models import User, UserRole
from tests.factories import make_user

probe = APIRouter(prefix="/probe")


@probe.get("/anyone")
def anyone_signed_in(user: CurrentUser) -> dict[str, str]:
    return {"seen": user.email}


@probe.get("/admin-only")
def admin_only(user: AdminUser) -> dict[str, str]:
    return {"seen": user.email}


app.include_router(probe)


def sign_in_as(client: TestClient, user: User) -> None:
    token = create_access_token(str(user.id), user.role.value)
    client.cookies.set(get_settings().cookie_name, token)


def test_a_customer_reaches_a_route_open_to_any_account(client: TestClient, db: Session) -> None:
    sign_in_as(client, make_user(db))

    assert client.get("/probe/anyone").status_code == 200


def test_a_customer_is_turned_away_from_an_admin_route(client: TestClient, db: Session) -> None:
    sign_in_as(client, make_user(db, role=UserRole.CUSTOMER))

    response = client.get("/probe/admin-only")

    assert response.status_code == 403
    assert response.json()["detail"] == "Your account cannot do that."


def test_an_admin_reaches_an_admin_route(client: TestClient, db: Session) -> None:
    sign_in_as(client, make_user(db, role=UserRole.ADMIN))

    assert client.get("/probe/admin-only").status_code == 200


def test_a_stranger_is_asked_to_sign_in_rather_than_told_they_lack_rights(
    client: TestClient,
) -> None:
    """401 and 403 mean different things: not signed in, versus signed in without rights."""
    assert client.get("/probe/admin-only").status_code == 401


def test_losing_admin_takes_effect_immediately(client: TestClient, db: Session) -> None:
    """The role is read from the account each request, not carried in the token."""
    user = make_user(db, role=UserRole.ADMIN)
    sign_in_as(client, user)
    assert client.get("/probe/admin-only").status_code == 200

    user.role = UserRole.CUSTOMER
    db.flush()

    assert client.get("/probe/admin-only").status_code == 403
