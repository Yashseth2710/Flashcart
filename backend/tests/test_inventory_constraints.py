"""The database refuses to record impossible stock, whatever the caller asks for.

These are the guarantees the reservation engine will lean on, so they are tested
against real Postgres constraints rather than application logic.
"""

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from tests.factories import make_inventory, make_sale_product


def test_available_is_what_is_left_after_holds_and_sales(db: Session) -> None:
    inventory = make_inventory(db, total=100, reserved=20, sold=65)

    assert inventory.available_quantity == 15


def test_stock_can_be_committed_up_to_the_total(db: Session) -> None:
    inventory = make_inventory(db, total=10, reserved=7, sold=3)

    assert inventory.available_quantity == 0


def test_holding_more_than_exists_is_refused(db: Session) -> None:
    inventory = make_inventory(db, total=10, reserved=3, sold=3)
    inventory.reserved_quantity = 8

    with pytest.raises(IntegrityError, match="ck_inventory_committed_within_total"):
        db.flush()


def test_selling_more_than_exists_is_refused(db: Session) -> None:
    inventory = make_inventory(db, total=10)
    inventory.sold_quantity = 11

    with pytest.raises(IntegrityError, match="ck_inventory_committed_within_total"):
        db.flush()


@pytest.mark.parametrize("column", ["total_quantity", "reserved_quantity", "sold_quantity"])
def test_quantities_cannot_go_negative(db: Session, column: str) -> None:
    inventory = make_inventory(db, total=5)
    setattr(inventory, column, -1)

    with pytest.raises(IntegrityError):
        db.flush()


def test_a_sale_cannot_promise_more_than_it_was_allocated(db: Session) -> None:
    sale_product = make_sale_product(db, allocated=50, reserved=30, sold=20)
    sale_product.reserved_quantity = 31

    with pytest.raises(IntegrityError, match="ck_sale_products_committed_within_allocation"):
        db.flush()


def test_a_sale_pool_tracks_its_own_availability(db: Session) -> None:
    sale_product = make_sale_product(db, allocated=50, reserved=30, sold=15)

    assert sale_product.available_quantity == 5
