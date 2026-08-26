"""Rules the schema keeps regardless of what the application does."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import FlashSale, Order, Reservation, ReservationStatus, User, UserRole
from tests.factories import make_sale_product, make_user, make_variant, unique


def test_two_people_cannot_share_an_email(db: Session) -> None:
    existing = make_user(db)
    db.add(
        User(
            name="Impostor",
            email=existing.email,
            password_hash="not-a-real-hash",
            role=UserRole.CUSTOMER,
        )
    )

    with pytest.raises(IntegrityError):
        db.flush()


def test_new_accounts_are_customers(db: Session) -> None:
    assert make_user(db).role is UserRole.CUSTOMER


def test_a_sale_cannot_end_before_it_starts(db: Session) -> None:
    start = datetime.now(UTC)
    db.add(FlashSale(name="Backwards", start_time=start, end_time=start - timedelta(minutes=1)))

    with pytest.raises(IntegrityError, match="ck_flash_sales_ends_after_start"):
        db.flush()


def test_the_same_product_cannot_be_listed_twice_in_one_sale(db: Session) -> None:
    sale_product = make_sale_product(db)
    duplicate = type(sale_product)(
        flash_sale_id=sale_product.flash_sale_id,
        variant_id=sale_product.variant_id,
        sale_price=sale_product.sale_price,
        allocated_quantity=5,
    )
    db.add(duplicate)

    with pytest.raises(IntegrityError, match="uq_sale_variant"):
        db.flush()


def test_a_reservation_must_expire_after_it_was_made(db: Session) -> None:
    sale_product = make_sale_product(db)
    db.add(
        Reservation(
            user=make_user(db),
            sale_product=sale_product,
            quantity=1,
            expires_at=datetime.now(UTC) - timedelta(minutes=1),
        )
    )

    with pytest.raises(IntegrityError, match="ck_reservations_expires_after_creation"):
        db.flush()


def test_a_reservation_starts_active(db: Session) -> None:
    reservation = Reservation(
        user=make_user(db),
        sale_product=make_sale_product(db),
        quantity=1,
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
    )
    db.add(reservation)
    db.flush()

    assert reservation.status is ReservationStatus.ACTIVE


def test_an_expired_hold_no_longer_claims_stock(db: Session) -> None:
    """Status alone does not grant a claim; the clock is checked too."""
    now = datetime.now(UTC)
    reservation = Reservation(
        user=make_user(db),
        sale_product=make_sale_product(db),
        quantity=1,
        expires_at=now + timedelta(minutes=5),
    )

    assert reservation.is_holding_stock(now) is True
    assert reservation.is_holding_stock(now + timedelta(minutes=6)) is False


def test_one_hold_cannot_become_two_orders(db: Session) -> None:
    """The unique reservation on orders is what stops a retry billing twice."""
    user = make_user(db)
    reservation = Reservation(
        user=user,
        sale_product=make_sale_product(db),
        quantity=1,
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
    )
    db.add(reservation)
    db.flush()

    for _ in range(2):
        db.add(
            Order(
                user=user,
                reservation=reservation,
                subtotal=Decimal("50.00"),
                total=Decimal("50.00"),
            )
        )

    with pytest.raises(IntegrityError):
        db.flush()


def test_a_variant_needs_a_unique_sku(db: Session) -> None:
    existing = make_variant(db)
    clone = type(existing)(
        product_id=existing.product_id, sku=existing.sku, name="Clone", price=existing.price
    )
    db.add(clone)

    with pytest.raises(IntegrityError):
        db.flush()


def test_a_product_slug_is_unique(db: Session) -> None:
    from app.models import Product

    existing = make_variant(db).product
    db.add(Product(name="Copy", slug=existing.slug, base_price=existing.base_price))

    with pytest.raises(IntegrityError):
        db.flush()


def test_unique_helper_does_not_repeat(db: Session) -> None:
    assert unique("x") != unique("x")


# How connections are held, which depends on where the app is running


def test_a_long_running_server_pools_connections() -> None:
    """Everyone queues on one locked row holding a connection while they wait,
    so the pool has to be deep enough for the queue."""
    from app.core.config import Settings
    from app.db.session import pool_for

    settings = Settings(vercel="")

    held = pool_for(settings)

    assert held["pool_size"] == settings.pool_size
    assert held["max_overflow"] == settings.pool_overflow
    assert "poolclass" not in held


def test_serverless_holds_no_pool_of_its_own() -> None:
    """A pool would be shared with nobody, and would multiply the connection
    count by however many instances happen to be awake."""
    from sqlalchemy.pool import NullPool

    from app.core.config import Settings
    from app.db.session import pool_for

    held = pool_for(Settings(vercel="1"))

    assert held["poolclass"] is NullPool
    assert "pool_size" not in held
    assert held["pool_pre_ping"] is True


def test_the_platform_is_read_rather_than_configured() -> None:
    """Vercel sets this itself, so nobody has to remember to."""
    from app.core.config import Settings

    assert Settings(vercel="1").serverless is True
    assert Settings(vercel="").serverless is False


# The session cookie, which has to cross domains once deployed


def test_a_cookie_no_browser_would_keep_is_refused() -> None:
    """SameSite=None without Secure is dropped silently, so the symptom is a
    sign-in that appears to work and then does not."""
    import pytest
    from pydantic import ValidationError

    from app.core.config import Settings

    with pytest.raises(ValidationError):
        Settings(cookie_samesite="none", cookie_secure=False)


def test_the_pairing_a_deployment_needs_is_allowed() -> None:
    from app.core.config import Settings

    settings = Settings(cookie_samesite="none", cookie_secure=True)

    assert settings.cookie_samesite == "none"


def test_the_local_default_stays_lax() -> None:
    """Nothing crosses a domain when the pages and the API share one."""
    from app.core.config import Settings

    assert Settings().cookie_samesite == "lax"
