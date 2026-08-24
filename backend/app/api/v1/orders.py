import uuid

from fastapi import APIRouter, status

from app.core.dependencies import CurrentUser, DbSession
from app.schemas.order import CheckoutWrite, Order
from app.services.order import OrderService

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("", response_model=list[Order])
def list_my_orders(db: DbSession, user: CurrentUser) -> list[Order]:
    """Everything this person has bought, newest first."""
    return OrderService(db).mine(user)


@router.post("", response_model=Order, status_code=status.HTTP_201_CREATED)
def check_out(payload: CheckoutWrite, db: DbSession, user: CurrentUser) -> Order:
    """Buy a hold. Repeating the same request returns the same order."""
    return OrderService(db).check_out(payload, user)


@router.get("/{order_id}", response_model=Order)
def read_order(order_id: uuid.UUID, db: DbSession, user: CurrentUser) -> Order:
    return OrderService(db).read(order_id, user)
