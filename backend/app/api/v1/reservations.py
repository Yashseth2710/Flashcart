import uuid

from fastapi import APIRouter, status

from app.core.dependencies import CurrentUser, DbSession
from app.core.limits import LimitHolds
from app.schemas.reservation import Hold, HoldWrite
from app.services.reservation import ReservationService

router = APIRouter(prefix="/holds", tags=["holds"])


@router.get("", response_model=list[Hold])
def list_my_holds(db: DbSession, user: CurrentUser) -> list[Hold]:
    """Everything this person has held, newest first."""
    return ReservationService(db).mine(user)


@router.post(
    "",
    response_model=Hold,
    status_code=status.HTTP_201_CREATED,
    dependencies=[LimitHolds],
)
def place_hold(payload: HoldWrite, db: DbSession, user: CurrentUser) -> Hold:
    """Put stock aside for a few minutes so it can be checked out."""
    return ReservationService(db).place(payload, user)


@router.get("/{reservation_id}", response_model=Hold)
def read_hold(reservation_id: uuid.UUID, db: DbSession, user: CurrentUser) -> Hold:
    return ReservationService(db).read(reservation_id, user)


@router.post("/{reservation_id}/release", response_model=Hold)
def release_hold(reservation_id: uuid.UUID, db: DbSession, user: CurrentUser) -> Hold:
    """Let it go early rather than waiting for it to run out."""
    return ReservationService(db).cancel(reservation_id, user)
