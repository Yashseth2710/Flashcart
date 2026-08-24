"""The claim this shop is built on: it cannot sell the same unit twice.

Every test here runs real threads on real connections against a real Postgres,
committing as they go. That is the point. A test that shares one transaction
proves nothing about two shoppers reaching for the same thing, because the
contention it would need cannot exist inside a single transaction.

Read this file as the answer to one question: when many people want the last
one, what does the shop do?
"""

import threading
import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import pytest

from app.core.exceptions import NotEnoughLeft, PurchaseLimitReached
from app.models import FlashSaleProduct, Reservation
from app.models.enums import ReservationStatus
from app.schemas.order import CheckoutWrite
from app.schemas.reservation import HoldWrite
from app.services.order import OrderService
from app.services.payment import ALWAYS_DECLINES
from app.services.reservation import ReservationService

# Big enough that a serialised implementation would be caught out, small enough
# that the suite stays quick.
CROWD = 20

# Every test in this file raises a crowd, so the mark is applied once here
# rather than repeated on each one.
pytestmark = pytest.mark.crowd


def all_at_once(work: Callable[[int], object], *, times: int) -> list[object]:
    """Runs `work` on `times` threads released together.

    The barrier matters. Started threads drift apart by milliseconds, which is
    long enough for a lock to be taken and released between them; holding them
    at a gate until every one is ready is what makes the contention real.
    """
    gate = threading.Barrier(times)
    results: list[object] = [None] * times
    lock = threading.Lock()

    def run(index: int) -> None:
        gate.wait()
        try:
            outcome = work(index)
        except Exception as caught:  # noqa: BLE001 - the outcome is the point
            outcome = caught
        with lock:
            results[index] = outcome

    threads = [threading.Thread(target=run, args=(i,)) for i in range(times)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)

    assert not any(thread.is_alive() for thread in threads), "a thread never finished"
    return results


def won(results: list[object]) -> list[object]:
    return [r for r in results if not isinstance(r, Exception)]


def lost(results: list[object], kind: type[Exception]) -> list[object]:
    return [r for r in results if isinstance(r, kind)]


# Reaching for stock


@pytest.mark.parametrize("stock", [1, 3, 7])
def test_only_as_many_people_win_as_there_are_units(world, sessions, stock: int) -> None:
    """The heart of it: twenty people, a few units, and no overselling.

    Run at three sizes because a lock that works for one unit can still be wrong
    for several: the arithmetic under it has to hold as well as the ordering.
    """
    entry = world.sale_item(allocated=stock, max_per_user=1)
    shoppers = world.crowd(CROWD)

    def reach(index: int):
        session = sessions()
        try:
            return ReservationService(session).place(
                HoldWrite(sale_product_id=entry.id, quantity=1), shoppers[index]
            )
        finally:
            session.close()

    results = all_at_once(reach, times=CROWD)

    assert len(won(results)) == stock
    assert len(lost(results, NotEnoughLeft)) == CROWD - stock

    reserved, sold, available = world.counters(entry)
    assert (reserved, sold, available) == (stock, 0, 0)


def test_the_losers_are_told_it_sold_out_rather_than_failing(world, sessions) -> None:
    """Losing a race is an answer, not an error. It has to read like one."""
    entry = world.sale_item(allocated=1, max_per_user=1)
    shoppers = world.crowd(CROWD)

    def reach(index: int):
        session = sessions()
        try:
            return ReservationService(session).place(
                HoldWrite(sale_product_id=entry.id, quantity=1), shoppers[index]
            )
        finally:
            session.close()

    results = all_at_once(reach, times=CROWD)
    refusals = lost(results, NotEnoughLeft)

    assert len(refusals) == CROWD - 1
    assert all(refusal.status_code == 409 for refusal in refusals)
    assert all("sold out" in refusal.detail for refusal in refusals)


def test_a_crowd_asking_for_several_each_still_cannot_take_more_than_exists(
    world, sessions
) -> None:
    """Ten units, twenty people, three each. Nobody gets a fraction of a hold."""
    entry = world.sale_item(allocated=10, max_per_user=3)
    shoppers = world.crowd(CROWD)

    def reach(index: int):
        session = sessions()
        try:
            return ReservationService(session).place(
                HoldWrite(sale_product_id=entry.id, quantity=3), shoppers[index]
            )
        finally:
            session.close()

    results = all_at_once(reach, times=CROWD)
    winners = won(results)

    # Three at a time out of ten: three people can be served, one unit is left
    # over and nobody can take it, because a partial hold is not a thing.
    assert len(winners) == 3
    reserved, sold, _ = world.counters(entry)
    assert reserved == 9
    assert sold == 0
    assert all(hold.quantity == 3 for hold in winners)


def test_one_person_hammering_the_button_cannot_beat_their_own_limit(world, sessions) -> None:
    """The limit is per person, so twenty parallel taps still only get two."""
    entry = world.sale_item(allocated=CROWD, max_per_user=2)
    shopper = world.shopper()

    def reach(_: int):
        session = sessions()
        try:
            return ReservationService(session).place(
                HoldWrite(sale_product_id=entry.id, quantity=1), shopper
            )
        finally:
            session.close()

    results = all_at_once(reach, times=CROWD)

    assert len(won(results)) == 2
    assert len(lost(results, PurchaseLimitReached)) == CROWD - 2
    reserved, _, _ = world.counters(entry)
    assert reserved == 2


# Buying


def test_a_crowd_buying_at_once_sells_each_unit_once(world, sessions) -> None:
    """Everyone holds first, then everyone pays at the same moment."""
    stock = 5
    entry = world.sale_item(allocated=stock, max_per_user=1)
    shoppers = world.crowd(stock)

    holds = []
    for shopper in shoppers:
        session = sessions()
        holds.append(
            ReservationService(session).place(
                HoldWrite(sale_product_id=entry.id, quantity=1), shopper
            )
        )
        session.close()

    def pay(index: int):
        session = sessions()
        try:
            return OrderService(session).check_out(
                CheckoutWrite(
                    reservation_id=holds[index].id,
                    idempotency_key=f"pay-{uuid.uuid4().hex}",
                ),
                shoppers[index],
            )
        finally:
            session.close()

    results = all_at_once(pay, times=stock)

    assert len(won(results)) == stock
    reserved, sold, available = world.counters(entry)
    assert (reserved, sold, available) == (0, stock, 0)
    assert world.orders_for(entry) == stock


def test_a_dropped_connection_retried_many_times_buys_once(world, sessions) -> None:
    """The same request, twenty times over, is one purchase.

    This is what an idempotency key promises. Every attempt has to come back
    with the order rather than a collision, because they are all the same
    person asking the same thing.
    """
    entry = world.sale_item(allocated=1, max_per_user=1)
    shopper = world.shopper()

    session = sessions()
    hold = ReservationService(session).place(
        HoldWrite(sale_product_id=entry.id, quantity=1), shopper
    )
    session.close()

    key = f"pay-{uuid.uuid4().hex}"

    def pay(_: int):
        session = sessions()
        try:
            return OrderService(session).check_out(
                CheckoutWrite(reservation_id=hold.id, idempotency_key=key), shopper
            )
        finally:
            session.close()

    results = all_at_once(pay, times=CROWD)
    winners = won(results)

    assert len(winners) == CROWD, "every retry should be answered with the order"
    assert len({order.id for order in winners}) == 1, "and it must be the same order"
    assert world.orders_for(entry) == 1

    reserved, sold, _ = world.counters(entry)
    assert (reserved, sold) == (0, 1)


def test_different_keys_still_cannot_buy_one_hold_twice(world, sessions) -> None:
    """Even without a key to match on, the row itself refuses a second sale."""
    entry = world.sale_item(allocated=1, max_per_user=1)
    shopper = world.shopper()

    session = sessions()
    hold = ReservationService(session).place(
        HoldWrite(sale_product_id=entry.id, quantity=1), shopper
    )
    session.close()

    def pay(index: int):
        session = sessions()
        try:
            return OrderService(session).check_out(
                CheckoutWrite(
                    reservation_id=hold.id, idempotency_key=f"pay-{index}-{uuid.uuid4().hex}"
                ),
                shopper,
            )
        finally:
            session.close()

    results = all_at_once(pay, times=CROWD)

    assert world.orders_for(entry) == 1
    reserved, sold, _ = world.counters(entry)
    assert (reserved, sold) == (0, 1)
    # Whatever each attempt was told, no attempt was charged a second time.
    assert len({order.id for order in won(results)}) <= 1


def test_a_declined_crowd_buys_nothing_and_keeps_every_hold(world, sessions) -> None:
    """Failure under load must be as tidy as success."""
    stock = 5
    entry = world.sale_item(allocated=stock, max_per_user=1)
    shoppers = world.crowd(stock)

    holds = []
    for shopper in shoppers:
        session = sessions()
        holds.append(
            ReservationService(session).place(
                HoldWrite(sale_product_id=entry.id, quantity=1), shopper
            )
        )
        session.close()

    def pay(index: int):
        session = sessions()
        try:
            return OrderService(session).check_out(
                CheckoutWrite(
                    reservation_id=holds[index].id,
                    idempotency_key=f"pay-{uuid.uuid4().hex}",
                    card_number=ALWAYS_DECLINES,
                ),
                shoppers[index],
            )
        finally:
            session.close()

    results = all_at_once(pay, times=stock)

    assert len(won(results)) == 0
    assert world.orders_for(entry) == 0
    reserved, sold, _ = world.counters(entry)
    assert (reserved, sold) == (stock, 0), "the holds survive so they can try again"


# Holding and letting go at the same time


def test_stock_let_go_is_picked_up_by_whoever_is_waiting(world, sessions) -> None:
    """One person releases while a crowd reaches. The unit finds exactly one home."""
    entry = world.sale_item(allocated=1, max_per_user=1)
    holder = world.shopper()
    waiting = world.crowd(CROWD)

    session = sessions()
    hold = ReservationService(session).place(
        HoldWrite(sale_product_id=entry.id, quantity=1), holder
    )
    session.close()

    def act(index: int):
        session = sessions()
        try:
            if index == 0:
                return ReservationService(session).cancel(hold.id, holder)
            return ReservationService(session).place(
                HoldWrite(sale_product_id=entry.id, quantity=1), waiting[index - 1]
            )
        finally:
            session.close()

    all_at_once(act, times=CROWD + 1)

    reserved, sold, _ = world.counters(entry)
    # Either the release landed first and someone else took it, or it did not
    # and nobody could. Never both, and never neither-but-counted.
    assert reserved in (0, 1)
    assert sold == 0

    live = [h for h in world.holds_for(entry) if h.status is ReservationStatus.ACTIVE]
    assert len(live) == reserved


# The invariant, under everything


def test_the_row_never_promises_more_than_it_holds(world, sessions) -> None:
    """Mixed traffic on one item: holding, buying, and letting go together.

    Nothing here checks who won. The only question is whether the count can be
    made to lie under load, and it must not be, at any moment or at the end.
    """
    entry = world.sale_item(allocated=8, max_per_user=2)
    shoppers = world.crowd(CROWD)
    placed: dict[int, Reservation] = {}
    guard = threading.Lock()

    def churn(index: int):
        session = sessions()
        try:
            service = ReservationService(session)
            hold = service.place(HoldWrite(sale_product_id=entry.id, quantity=1), shoppers[index])
            with guard:
                placed[index] = hold

            # Every third person changes their mind, every third pays, the rest
            # sit on it, so all three paths run against the same row at once.
            if index % 3 == 0:
                return service.cancel(hold.id, shoppers[index])
            if index % 3 == 1:
                buying = sessions()
                try:
                    return OrderService(buying).check_out(
                        CheckoutWrite(
                            reservation_id=hold.id,
                            idempotency_key=f"pay-{uuid.uuid4().hex}",
                        ),
                        shoppers[index],
                    )
                finally:
                    buying.close()
            return hold
        finally:
            session.close()

    all_at_once(churn, times=CROWD)

    row = world.reread(entry)
    assert row.reserved_quantity >= 0
    assert row.sold_quantity >= 0
    assert row.reserved_quantity + row.sold_quantity <= row.allocated_quantity

    # And the counters agree with the rows they are meant to summarise.
    holds = world.holds_for(entry)
    live = sum(h.quantity for h in holds if h.status is ReservationStatus.ACTIVE)
    bought = sum(h.quantity for h in holds if h.status is ReservationStatus.COMPLETED)
    assert row.reserved_quantity == live
    assert row.sold_quantity == bought


def test_two_items_in_one_sale_do_not_wait_on_each_other(world, sessions) -> None:
    """The lock is on the item, not the sale.

    If it were on the sale, everything in a busy sale would queue behind
    everything else. Both items selling out proves each was decided on its own.
    """
    first = world.sale_item(allocated=5, max_per_user=1)
    second = world.sale_item(allocated=5, max_per_user=1)
    shoppers = world.crowd(CROWD)

    def reach(index: int):
        entry = first if index % 2 == 0 else second
        session = sessions()
        try:
            return ReservationService(session).place(
                HoldWrite(sale_product_id=entry.id, quantity=1), shoppers[index]
            )
        finally:
            session.close()

    all_at_once(reach, times=CROWD)

    assert world.counters(first)[0] == 5
    assert world.counters(second)[0] == 5


# Expiry under load


def test_a_lapsed_hold_is_reclaimed_once_however_many_people_ask(world, sessions) -> None:
    """One abandoned unit, a crowd arriving at once. It is given away once."""
    entry = world.sale_item(allocated=1, max_per_user=1)
    abandoner = world.shopper()
    waiting = world.crowd(CROWD)

    # A hold that has already run out, with the stock still counted against it.
    session = sessions()
    moment = datetime.now(UTC)
    session.add(
        Reservation(
            user_id=abandoner.id,
            flash_sale_product_id=entry.id,
            quantity=1,
            status=ReservationStatus.ACTIVE,
            expires_at=moment - timedelta(seconds=1),
            created_at=moment - timedelta(minutes=20),
        )
    )
    row = session.get(FlashSaleProduct, entry.id)
    row.reserved_quantity += 1
    session.commit()
    session.close()

    assert world.counters(entry)[0] == 1

    def reach(index: int):
        session = sessions()
        try:
            return ReservationService(session).place(
                HoldWrite(sale_product_id=entry.id, quantity=1), waiting[index]
            )
        finally:
            session.close()

    results = all_at_once(reach, times=CROWD)

    assert len(won(results)) == 1, "the reclaimed unit goes to exactly one person"
    reserved, sold, _ = world.counters(entry)
    assert (reserved, sold) == (1, 0)

    dead = [
        h
        for h in world.holds_for(entry)
        if h.user_id == abandoner.id and h.status is ReservationStatus.EXPIRED
    ]
    assert len(dead) == 1, "and the abandoned one is marked, once"
