import hashlib
import time
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import (
    HoldAlreadyBought,
    KeyReusedOnDifferentRequest,
    OrderNotFound,
    PaymentDeclined,
    ReservationNotActive,
    ReservationNotFound,
)
from app.models import Order as OrderRow
from app.models import OrderItem, User
from app.models.enums import IdempotencyStatus, OrderStatus, ReservationStatus
from app.repositories.order import OrderRepository
from app.repositories.reservation import ReservationRepository
from app.schemas.order import CheckoutWrite, Order, OrderLine
from app.services.payment import PaymentGateway

# How long a used key is remembered. Long enough to cover any retry a client
# would sensibly make, short enough that the table does not grow forever.
KEY_LIFETIME = timedelta(hours=24)

# How long a request that lost the race waits for the winner to commit before
# giving up on returning its order. Short: the winner is already mid-flight.
SETTLE_TRIES = 4
SETTLE_PAUSE = 0.15


class Settled(Exception):
    """Carries an order that a competing copy of this request already produced.

    Internal to this module: it unwinds the attempt in progress and hands the
    finished order back, so a retry reads as success rather than a collision.
    """

    def __init__(self, order: Order) -> None:
        super().__init__("already settled")
        self.order = order


def now() -> datetime:
    return datetime.now(UTC)


class OrderService:
    """Turning a hold into a purchase.

    A hold is the right to buy; this is the buying. The units move from reserved
    to sold on the same row, under the same lock the hold was taken under, so the
    total committed never changes at the moment of sale and the invariant the
    database enforces is never even briefly untrue.

    Two separate things stop a double charge, because they fail differently:

    The unique index on orders.reservation_id means one hold can produce at most
    one order, whatever the caller does. That is the guarantee.

    The idempotency key means a retry of the *same* request gets the *same*
    order back rather than an error. That is the courtesy. It also refuses a key
    reused with a different body, which would otherwise return a result that has
    nothing to do with what was asked for.
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self.orders = OrderRepository(db)
        self.holds = ReservationRepository(db)
        self.gateway = PaymentGateway()

    # Reading

    def describe(self, order: OrderRow) -> Order:
        hold = order.reservation
        sale_name = None
        if hold is not None and hold.sale_product is not None:
            sale_name = hold.sale_product.flash_sale.name

        lines = []
        for item in order.items:
            product = self.orders.product_for_variant(item.variant_id) if item.variant_id else None
            lines.append(
                OrderLine(
                    id=item.id,
                    product_name=item.product_name_snapshot,
                    price=item.price_snapshot,
                    quantity=item.quantity,
                    line_total=item.price_snapshot * item.quantity,
                    # The catalogue may have moved on; a line still reads
                    # correctly without it, so both are optional.
                    product_slug=product.slug if product else None,
                    image_url=product.image_url if product else None,
                )
            )

        return Order(
            id=order.id,
            status=order.status.value,
            subtotal=order.subtotal,
            total=order.total,
            placed_at=order.created_at,
            sale_name=sale_name,
            items=lines,
        )

    def mine(self, user: User) -> list[Order]:
        return [self.describe(order) for order in self.orders.for_user(user.id)]

    def read(self, order_id: uuid.UUID, user: User) -> Order:
        order = self.orders.get(order_id)
        # Someone else's order is reported as missing rather than forbidden, so
        # ids cannot be probed for existence.
        if order is None or order.user_id != user.id:
            raise OrderNotFound
        return self.describe(order)

    # Buying

    def _fingerprint(self, payload: CheckoutWrite) -> str:
        """What the key is a key *for*. Only the parts that decide the outcome."""
        return hashlib.sha256(str(payload.reservation_id).encode()).hexdigest()

    def check_out(self, payload: CheckoutWrite, user: User) -> Order:
        fingerprint = self._fingerprint(payload)

        settled = self._already_done(payload, user, fingerprint)
        if settled is not None:
            return settled

        hold = self.holds.get(payload.reservation_id)
        if hold is None or hold.user_id != user.id:
            raise ReservationNotFound

        # Locked before anything is read from it, so a checkout cannot race an
        # expiry sweep or a cancel on the same hold.
        entry = self.holds.lock_sale_product(hold.flash_sale_product_id)
        self.db.refresh(hold)
        moment = now()

        if hold.status is ReservationStatus.COMPLETED:
            # Bought already. If it was this person who bought it, they are owed
            # that order rather than an error: a retry arriving just after the
            # winner committed lands here, and it is the same purchase.
            bought = self.orders.for_reservation(hold.id)
            if bought is not None and bought.user_id == user.id:
                return self.describe(bought)
            raise ReservationNotActive(hold.status.value)

        if hold.status is not ReservationStatus.ACTIVE:
            raise ReservationNotActive(hold.status.value)

        if hold.expires_at <= moment:
            # It ran out while they were paying. Say so, and hand the stock back
            # in the same breath rather than leaving it stranded.
            hold.status = ReservationStatus.EXPIRED
            if entry is not None:
                entry.reserved_quantity -= hold.quantity
            self.db.commit()
            raise ReservationNotActive(ReservationStatus.EXPIRED.value)

        subtotal = entry.sale_price * hold.quantity

        # Taken before the charge, so a retry that arrives while this one is
        # still paying cannot charge a second time.
        try:
            claim = self._claim(payload, user, fingerprint)
        except Settled as already:
            # A copy of this same request finished first. Its order is the answer.
            return already.order

        charge = self.gateway.charge(amount=subtotal, card_number=payload.card_number)
        if charge is None:
            # Nothing was taken, so the hold survives and they can try again.
            # The claim goes too, or the retry would look like a duplicate.
            self.db.delete(claim)
            self.db.commit()
            raise PaymentDeclined

        product = self.orders.product_for_variant(entry.variant_id)
        order = OrderRow(
            user_id=user.id,
            reservation_id=hold.id,
            status=OrderStatus.PAID,
            subtotal=subtotal,
            total=subtotal,
        )
        order.items.append(
            OrderItem(
                variant_id=entry.variant_id,
                product_name_snapshot=product.name if product else "Item",
                price_snapshot=entry.sale_price,
                quantity=hold.quantity,
            )
        )
        self.db.add(order)

        # The units were already committed when the hold was placed. Selling
        # moves them across rather than adding to them, so the total the row
        # carries does not change and the invariant holds throughout.
        entry.reserved_quantity -= hold.quantity
        entry.sold_quantity += hold.quantity
        hold.status = ReservationStatus.COMPLETED

        claim.status = IdempotencyStatus.COMPLETED
        claim.response_reference = order.id

        try:
            self.db.commit()
        except IntegrityError:
            # The unique index on reservation_id had the last word: another
            # request bought this hold first. Nothing here is written.
            self.db.rollback()

            # That winner is this same person retrying, so its order is what
            # they are owed. Looked for on a fresh connection, since the
            # rollback left this session unable to see the newer commit.
            for attempt in range(SETTLE_TRIES):
                existing = self._settled_elsewhere(payload, user)
                if existing is not None:
                    return existing
                if attempt < SETTLE_TRIES - 1:
                    time.sleep(SETTLE_PAUSE)

            raise HoldAlreadyBought from None

        return self.read(order.id, user)

    def _already_done(self, payload: CheckoutWrite, user: User, fingerprint: str) -> Order | None:
        """Whether this exact request has already been answered."""
        seen = self.orders.find_key(user_id=user.id, key=payload.idempotency_key)
        if seen is None:
            return None

        if seen.request_hash != fingerprint:
            raise KeyReusedOnDifferentRequest

        if seen.status is IdempotencyStatus.COMPLETED and seen.response_reference:
            order = self.orders.get(seen.response_reference)
            if order is not None and order.user_id == user.id:
                return self.describe(order)

        # Claimed but unfinished: the first attempt is still in flight, or it
        # died. Either way the hold is the authority on what happened.
        existing = self.orders.for_reservation(payload.reservation_id)
        if existing is not None and existing.user_id == user.id:
            return self.describe(existing)
        return None

    def _claim(self, payload: CheckoutWrite, user: User, fingerprint: str):
        """Takes the key, or raises Settled carrying the order that already won.

        Losing this race is not a failure. It means another copy of *this same
        request* got there first, and the caller is owed that copy's result
        rather than an error: retrying is exactly what an idempotency key is for.
        """
        try:
            return self.orders.claim_key(
                user_id=user.id,
                key=payload.idempotency_key,
                request_hash=fingerprint,
                expires_at=now() + KEY_LIFETIME,
            )
        except IntegrityError:
            self.db.rollback()

        # The winner may still be paying. Give it a moment and look again rather
        # than reporting a collision the caller cannot act on: the order it is
        # about to write is this caller's own, and is the answer they are owed.
        #
        # The looking is done on its own connection. Reading it on this session
        # would need the transaction ended between tries, and ending it here
        # would throw away work the caller still owns.
        for attempt in range(SETTLE_TRIES):
            found = self._settled_elsewhere(payload, user)
            if found is not None:
                raise Settled(found)
            if attempt < SETTLE_TRIES - 1:
                time.sleep(SETTLE_PAUSE)

        # Still nothing: the first attempt died before writing, or was declined.
        # Saying the hold is taken is honest, and a fresh key will get through.
        raise HoldAlreadyBought

    def _settled_elsewhere(self, payload: CheckoutWrite, user: User) -> Order | None:
        """Whether another transaction has committed an order for this hold.

        Opened and closed per look, so each one sees the newest committed state
        rather than a snapshot taken before the winner finished.
        """
        from app.db.session import get_session_factory

        with get_session_factory()() as fresh:
            order = OrderRepository(fresh).for_reservation(payload.reservation_id)
            if order is None or order.user_id != user.id:
                return None
            return OrderService(fresh).describe(order)
