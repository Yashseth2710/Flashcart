import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from app.schemas.flash_sale import SaleStatus


class SavedItem(BaseModel):
    """A saved product, described with whatever is true of it right now.

    Saving records only which product; everything else here is read at the
    moment of asking, so a product that has since entered a sale says so.
    """

    id: uuid.UUID
    product_id: uuid.UUID
    product_name: str
    product_slug: str
    image_url: str | None
    brand: str | None
    normal_price: Decimal
    saved_at: datetime

    # Filled in when the product is in a sale that is on or coming.
    sale_id: uuid.UUID | None = None
    sale_name: str | None = None
    sale_status: SaleStatus | None = None
    sale_price: Decimal | None = None
    sale_product_id: uuid.UUID | None = None
    available_quantity: int | None = None
    starts_at: datetime | None = None


class SavedWrite(BaseModel):
    product_id: uuid.UUID


class Reminder(BaseModel):
    id: uuid.UUID
    sale_id: uuid.UUID
    sale_name: str
    description: str | None
    starts_at: datetime
    ends_at: datetime
    status: SaleStatus
    item_count: int
    # How many of this person's saved products are in the sale, which is the
    # reason the reminder was worth setting.
    saved_in_sale: int


class ReminderWrite(BaseModel):
    flash_sale_id: uuid.UUID


class Waiting(BaseModel):
    """What is worth telling someone the moment they arrive.

    Read on every page, so it stays small: counts and the one sale that matters
    most, rather than everything they have ever marked.
    """

    saved_count: int
    reminder_count: int
    # A sale they asked to be reminded of that is running now. The whole point
    # of the reminder, and the only thing urgent enough to interrupt with.
    open_now: Reminder | None = None
    opening_next: Reminder | None = None
