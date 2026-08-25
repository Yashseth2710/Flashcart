import uuid

from fastapi import APIRouter, Response, status

from app.core.dependencies import CurrentUser, DbSession
from app.core.limits import LimitMarks
from app.schemas.saved import Reminder, ReminderWrite, SavedItem, SavedWrite, Waiting
from app.services.saved import SavedService

router = APIRouter(tags=["saved"])


@router.get("/saved", response_model=list[SavedItem])
def list_saved(db: DbSession, user: CurrentUser) -> list[SavedItem]:
    """Everything this person has saved, newest first, with where each one
    currently stands in a sale."""
    return SavedService(db).mine(user)


@router.post(
    "/saved",
    response_model=SavedItem,
    status_code=status.HTTP_201_CREATED,
    dependencies=[LimitMarks],
)
def save_product(payload: SavedWrite, db: DbSession, user: CurrentUser) -> SavedItem:
    """Saving something already saved is answered rather than refused."""
    return SavedService(db).save(payload.product_id, user)


@router.delete(
    "/saved/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[LimitMarks],
)
def forget_product(product_id: uuid.UUID, db: DbSession, user: CurrentUser) -> Response:
    SavedService(db).forget(product_id, user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/reminders", response_model=list[Reminder])
def list_reminders(db: DbSession, user: CurrentUser) -> list[Reminder]:
    """Sales this person asked to be shown, soonest first. Finished ones are gone."""
    return SavedService(db).my_reminders(user)


@router.post(
    "/reminders",
    response_model=Reminder,
    status_code=status.HTTP_201_CREATED,
    dependencies=[LimitMarks],
)
def remind_me(payload: ReminderWrite, db: DbSession, user: CurrentUser) -> Reminder:
    return SavedService(db).remind_me(payload.flash_sale_id, user)


@router.delete(
    "/reminders/{sale_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[LimitMarks],
)
def forget_sale(sale_id: uuid.UUID, db: DbSession, user: CurrentUser) -> Response:
    SavedService(db).forget_sale(sale_id, user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/waiting", response_model=Waiting)
def what_is_waiting(db: DbSession, user: CurrentUser) -> Waiting:
    """The small summary the header asks for on every page."""
    return SavedService(db).waiting_for(user)
