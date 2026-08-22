import uuid
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class VariantSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sku: str
    name: str
    price: Decimal
    available_quantity: int


class ProductSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    category: str | None
    brand: str | None
    image_url: str | None
    base_price: Decimal


class ProductDetail(ProductSummary):
    description: str | None
    is_active: bool
    variants: list[VariantSummary]


class ProductPage(BaseModel):
    items: list[ProductSummary]
    total: int
    limit: int
    offset: int


class ProductWrite(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    category: str | None = Field(default=None, max_length=80)
    brand: str | None = Field(default=None, max_length=120)
    image_url: str | None = Field(default=None, max_length=500)
    base_price: Decimal = Field(ge=0, decimal_places=2)
    is_active: bool = True


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    category: str | None = Field(default=None, max_length=80)
    brand: str | None = Field(default=None, max_length=120)
    image_url: str | None = Field(default=None, max_length=500)
    base_price: Decimal | None = Field(default=None, ge=0, decimal_places=2)
    is_active: bool | None = None


class StockWrite(BaseModel):
    variant_id: uuid.UUID
    total_quantity: int = Field(ge=0)


class StockLevel(BaseModel):
    variant_id: uuid.UUID
    sku: str
    total_quantity: int
    reserved_quantity: int
    sold_quantity: int
    available_quantity: int
