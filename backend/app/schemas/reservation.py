import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

HoldStatus = Literal["ACTIVE", "COMPLETED", "EXPIRED", "CANCELLED"]


class HoldWrite(BaseModel):
    sale_product_id: uuid.UUID
    quantity: int = Field(ge=1)


class Hold(BaseModel):
    """A hold, described the way the person who placed it would read it.

    status is what the hold is *now*, not what the row happens to say: one whose
    time has run out reads EXPIRED here even if no sweep has touched it yet.
    """

    id: uuid.UUID
    sale_product_id: uuid.UUID
    quantity: int
    status: HoldStatus
    expires_at: datetime
    seconds_remaining: int
    created_at: datetime

    sale_id: uuid.UUID
    sale_name: str
    product_name: str
    product_slug: str
    image_url: str | None
    sku: str
    sale_price: Decimal
    line_total: Decimal
