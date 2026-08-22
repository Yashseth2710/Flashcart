import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

SaleStatus = Literal["UPCOMING", "ACTIVE", "ENDED"]


class SaleItem(BaseModel):
    """One product on sale, with what is left of its allocation."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    variant_id: uuid.UUID
    product_name: str
    product_slug: str
    image_url: str | None
    sku: str
    normal_price: Decimal
    sale_price: Decimal
    allocated_quantity: int
    available_quantity: int
    max_per_user: int


class SaleSummary(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    start_time: datetime
    end_time: datetime
    status: SaleStatus
    item_count: int


class SaleDetail(SaleSummary):
    items: list[SaleItem]


class SaleWrite(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    start_time: datetime
    end_time: datetime

    @model_validator(mode="after")
    def _ends_after_it_starts(self) -> "SaleWrite":
        if self.end_time <= self.start_time:
            raise ValueError("A sale must end after it starts.")
        return self


class SaleItemWrite(BaseModel):
    variant_id: uuid.UUID
    sale_price: Decimal = Field(ge=0, decimal_places=2)
    allocated_quantity: int = Field(ge=1)
    max_per_user: int = Field(ge=1, default=1)

    @model_validator(mode="after")
    def _limit_within_allocation(self) -> "SaleItemWrite":
        if self.max_per_user > self.allocated_quantity:
            raise ValueError("Nobody can buy more than the sale holds.")
        return self
