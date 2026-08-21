import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import (
    FlashSale,
    FlashSaleProduct,
    Inventory,
    Product,
    ProductVariant,
    User,
    UserRole,
)


def unique(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


def make_user(db: Session, *, role: UserRole = UserRole.CUSTOMER) -> User:
    user = User(
        name="Test Person",
        email=f"{unique('person')}@example.com",
        password_hash="not-a-real-hash",
        role=role,
    )
    db.add(user)
    db.flush()
    return user


def make_variant(db: Session, *, price: str = "100.00") -> ProductVariant:
    product = Product(name="Test Product", slug=unique("product"), base_price=Decimal(price))
    variant = ProductVariant(
        product=product, sku=unique("SKU"), name="Default", price=Decimal(price)
    )
    db.add_all([product, variant])
    db.flush()
    return variant


def make_inventory(db: Session, *, total: int = 10, reserved: int = 0, sold: int = 0) -> Inventory:
    inventory = Inventory(
        variant=make_variant(db),
        total_quantity=total,
        reserved_quantity=reserved,
        sold_quantity=sold,
    )
    db.add(inventory)
    db.flush()
    return inventory


def make_sale_product(
    db: Session,
    *,
    allocated: int = 5,
    reserved: int = 0,
    sold: int = 0,
    max_per_user: int = 1,
    starts_in: timedelta = timedelta(minutes=-5),
    runs_for: timedelta = timedelta(minutes=30),
) -> FlashSaleProduct:
    start = datetime.now(UTC) + starts_in
    sale = FlashSale(name="Test Sale", start_time=start, end_time=start + runs_for)
    sale_product = FlashSaleProduct(
        flash_sale=sale,
        variant=make_variant(db),
        sale_price=Decimal("50.00"),
        allocated_quantity=allocated,
        reserved_quantity=reserved,
        sold_quantity=sold,
        max_per_user=max_per_user,
    )
    db.add_all([sale, sale_product])
    db.flush()
    return sale_product
