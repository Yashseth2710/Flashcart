import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints

OrderState = Literal["PAID", "FULFILLED", "CANCELLED"]

# Long enough for a UUID or a hash, short enough to store comfortably.
IdempotencyKey = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=8, max_length=255)
]


class CheckoutWrite(BaseModel):
    """Buying one hold.

    The key is chosen by the caller and repeated if the request is retried, so a
    dropped connection or an impatient second tap settles as one order rather
    than two.
    """

    reservation_id: uuid.UUID
    idempotency_key: IdempotencyKey
    # Which card was used is not modelled; this stands in for the payment step
    # so the flow is honest about where one would go.
    card_number: Annotated[str, StringConstraints(strip_whitespace=True, min_length=4)] = Field(
        default="4242424242424242"
    )


class OrderLine(BaseModel):
    """A line as it was bought, not as the catalogue reads today."""

    id: uuid.UUID
    product_name: str
    price: Decimal
    quantity: int
    line_total: Decimal
    product_slug: str | None
    image_url: str | None


class Order(BaseModel):
    id: uuid.UUID
    status: OrderState
    subtotal: Decimal
    total: Decimal
    placed_at: datetime
    sale_name: str | None
    items: list[OrderLine]
