"""Fixtures for tests that need more than one connection at once.

The ordinary `db` fixture wraps a test in a transaction and rolls it back, which
keeps tests clean but makes real concurrency impossible to express: two threads
sharing one uncommitted transaction are not two shoppers, and neither can see
what the other has written.

What is here commits for real, on its own connections, and tidies up afterwards
by tracking what it made.
"""

import uuid
from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, delete, func, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.core.security import hash_password
from app.models import (
    FlashSale,
    FlashSaleProduct,
    IdempotencyKey,
    Inventory,
    Order,
    OrderItem,
    Product,
    ProductVariant,
    Reservation,
    User,
)

CROWD_PASSWORD = "a-long-enough-password"


@pytest.fixture(scope="session")
def committing_engine():
    """A pool big enough for a crowd to arrive at once.

    Sized above the largest crowd any test raises, so a thread waiting for a
    connection never looks like a thread waiting for a lock.
    """
    settings = get_settings()
    if not settings.database_configured:
        pytest.skip("DATABASE_URL is not set")
    engine = create_engine(settings.alembic_url, pool_size=30, max_overflow=20)
    yield engine
    engine.dispose()


@pytest.fixture
def sessions(committing_engine) -> Iterator[Callable[[], Session]]:
    """Hands out real sessions and closes every one of them afterwards."""
    factory = sessionmaker(bind=committing_engine, expire_on_commit=False)
    opened: list[Session] = []

    def open_one() -> Session:
        session = factory()
        opened.append(session)
        return session

    try:
        yield open_one
    finally:
        for session in opened:
            session.close()


@pytest.fixture
def world(sessions):
    """Builds committed rows and removes them however the test ends.

    Everything made is remembered, so a failure part-way through still leaves
    the database as it was found.
    """
    keeper = Keeper(sessions)
    try:
        yield keeper
    finally:
        keeper.clear()


class Keeper:
    def __init__(self, sessions: Callable[[], Session]) -> None:
        self.sessions = sessions
        self.db = sessions()
        self.users: list[uuid.UUID] = []
        self.sales: list[uuid.UUID] = []
        self.products: list[uuid.UUID] = []

    def _tag(self) -> str:
        return uuid.uuid4().hex[:10]

    def shopper(self) -> User:
        user = User(
            name="Crowd Member",
            email=f"crowd-{self._tag()}@example.com",
            password_hash=hash_password(CROWD_PASSWORD),
        )
        self.db.add(user)
        self.db.commit()
        self.users.append(user.id)
        return user

    def crowd(self, size: int) -> list[User]:
        return [self.shopper() for _ in range(size)]

    def sale_item(
        self,
        *,
        allocated: int = 1,
        max_per_user: int = 1,
        price: str = "10.00",
        starts_in: timedelta = timedelta(minutes=-1),
        runs_for: timedelta = timedelta(hours=1),
    ) -> FlashSaleProduct:
        """One product, in stock, in a sale that is running."""
        product = Product(
            name="Crowd Product", slug=f"crowd-{self._tag()}", base_price=Decimal(price)
        )
        variant = ProductVariant(
            product=product, sku=f"CROWD-{self._tag()}", name="Default", price=Decimal(price)
        )
        inventory = Inventory(variant=variant, total_quantity=allocated + 50)
        self.db.add_all([product, variant, inventory])
        self.db.flush()
        self.products.append(product.id)

        start = datetime.now(UTC) + starts_in
        sale = FlashSale(name="Crowd Sale", start_time=start, end_time=start + runs_for)
        # The units leave the warehouse for the sale, as a real allocation does.
        inventory.reserved_quantity += allocated
        entry = FlashSaleProduct(
            flash_sale=sale,
            variant=variant,
            sale_price=Decimal(price),
            allocated_quantity=allocated,
            max_per_user=max_per_user,
        )
        self.db.add_all([sale, entry])
        self.db.commit()
        self.sales.append(sale.id)
        return entry

    def reread(self, entry: FlashSaleProduct) -> FlashSaleProduct:
        """The row as it stands now, on a connection that has seen every commit."""
        fresh = self.sessions()
        try:
            return fresh.get(FlashSaleProduct, entry.id, populate_existing=True)
        finally:
            fresh.expunge_all()

    def counters(self, entry: FlashSaleProduct) -> tuple[int, int, int]:
        row = self.reread(entry)
        return (row.reserved_quantity, row.sold_quantity, row.available_quantity)

    def orders_for(self, entry: FlashSaleProduct) -> int:
        """How many orders exist against this item, counted from committed rows."""
        fresh = self.sessions()
        return (
            fresh.scalar(
                select(func.count())
                .select_from(Order)
                .join(Reservation, Reservation.id == Order.reservation_id)
                .where(Reservation.flash_sale_product_id == entry.id)
            )
            or 0
        )

    def holds_for(self, entry: FlashSaleProduct) -> list[Reservation]:
        fresh = self.sessions()
        return list(
            fresh.scalars(
                select(Reservation)
                .where(Reservation.flash_sale_product_id == entry.id)
                .execution_options(populate_existing=True)
            ).all()
        )

    def clear(self) -> None:
        """Unwinds child rows before their parents, so nothing is orphaned.

        Deletes are issued as statements rather than through the ORM. Doing both
        would have the session try to remove rows a cascade has already taken,
        which works but warns about it on every run and would drown a real
        complaint about a row that genuinely failed to go.
        """
        db = self.db
        try:
            variants = (
                db.scalars(
                    select(ProductVariant.id).where(ProductVariant.product_id.in_(self.products))
                ).all()
                if self.products
                else []
            )
            entries = (
                db.scalars(
                    select(FlashSaleProduct.id).where(
                        FlashSaleProduct.flash_sale_id.in_(self.sales)
                    )
                ).all()
                if self.sales
                else []
            )

            if self.users:
                db.execute(delete(IdempotencyKey).where(IdempotencyKey.user_id.in_(self.users)))
            if entries:
                holds = db.scalars(
                    select(Reservation.id).where(Reservation.flash_sale_product_id.in_(entries))
                ).all()
                if holds:
                    orders = db.scalars(
                        select(Order.id).where(Order.reservation_id.in_(holds))
                    ).all()
                    if orders:
                        db.execute(delete(OrderItem).where(OrderItem.order_id.in_(orders)))
                        db.execute(delete(Order).where(Order.id.in_(orders)))
                db.execute(
                    delete(Reservation).where(Reservation.flash_sale_product_id.in_(entries))
                )

            if self.users:
                leftover = db.scalars(select(Order.id).where(Order.user_id.in_(self.users))).all()
                if leftover:
                    db.execute(delete(OrderItem).where(OrderItem.order_id.in_(leftover)))
                    db.execute(delete(Order).where(Order.id.in_(leftover)))

            # The allocation goes back to the warehouse it was taken from, so a
            # run leaves stock counts exactly as it found them.
            for entry_id in entries:
                entry = db.get(FlashSaleProduct, entry_id)
                if entry is None:
                    continue
                inventory = db.scalar(
                    select(Inventory).where(Inventory.variant_id == entry.variant_id)
                )
                if inventory is not None:
                    inventory.reserved_quantity -= entry.allocated_quantity
            db.flush()

            if entries:
                db.execute(delete(FlashSaleProduct).where(FlashSaleProduct.id.in_(entries)))
            if self.sales:
                db.execute(delete(FlashSale).where(FlashSale.id.in_(self.sales)))
            if variants:
                db.execute(delete(Inventory).where(Inventory.variant_id.in_(variants)))
                db.execute(delete(ProductVariant).where(ProductVariant.id.in_(variants)))
            if self.products:
                db.execute(delete(Product).where(Product.id.in_(self.products)))
            if self.users:
                db.execute(delete(User).where(User.id.in_(self.users)))
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
