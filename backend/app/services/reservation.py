import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import (
    NotEnoughLeft,
    PurchaseLimitReached,
    ReservationNotActive,
    ReservationNotFound,
    SaleNotFound,
    SaleNotRunning,
)
from app.models import Reservation, User
from app.models.enums import ReservationStatus
from app.repositories.reservation import ReservationRepository
from app.schemas.reservation import Hold, HoldWrite


def now() -> datetime:
    return datetime.now(UTC)


class ReservationService:
    """Holds on sale stock.

    Placing a hold is the one operation where many people reach for the same
    thing at the same moment, so it is the one operation that locks. Everything
    else here reads.

    Two rules run through all of it:

    Expiry is read from the clock, never trusted from the row. A hold past its
    time stops counting the instant it passes, whether or not anything has been
    around to mark it. That means no sweep has to be running for the numbers to
    be right; the sweep only tidies up.

    The counters are the truth. reserved_quantity on the sale item is what stops
    overselling, and it is adjusted under the lock in the same transaction as the
    hold that caused it. A CHECK constraint refuses the write if the two ever
    disagree.
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self.holds = ReservationRepository(db)

    # Reading

    def _status_at(self, hold: Reservation, moment: datetime) -> str:
        """What the hold is now, rather than what the row was last told."""
        if hold.status is ReservationStatus.ACTIVE and hold.expires_at <= moment:
            return ReservationStatus.EXPIRED.value
        return hold.status.value

    def describe(self, hold: Reservation, at: datetime | None = None) -> Hold:
        moment = at or now()
        entry = hold.sale_product
        variant = entry.variant
        product = variant.product
        live = self._status_at(hold, moment)
        remaining = (hold.expires_at - moment).total_seconds()
        return Hold(
            id=hold.id,
            sale_product_id=entry.id,
            quantity=hold.quantity,
            status=live,
            expires_at=hold.expires_at,
            # Only a live hold has time left; a finished one reads zero rather
            # than a negative number counting up since it ended.
            seconds_remaining=max(0, int(remaining)) if live == "ACTIVE" else 0,
            created_at=hold.created_at,
            sale_id=entry.flash_sale_id,
            sale_name=entry.flash_sale.name,
            product_name=product.name,
            product_slug=product.slug,
            image_url=product.image_url,
            sku=variant.sku,
            sale_price=entry.sale_price,
            line_total=entry.sale_price * hold.quantity,
        )

    def mine(self, user: User) -> list[Hold]:
        moment = now()
        return [self.describe(hold, moment) for hold in self.holds.for_user(user.id)]

    def read(self, reservation_id: uuid.UUID, user: User) -> Hold:
        hold = self.holds.describe(reservation_id)
        # Someone else's hold is not theirs to see. Reported as missing rather
        # than forbidden, so ids cannot be probed for existence.
        if hold is None or hold.user_id != user.id:
            raise ReservationNotFound
        return self.describe(hold)

    # Writing

    def place(self, payload: HoldWrite, user: User) -> Hold:
        """Take stock off the shelf and put this person's name on it.

        Order matters. The sale item is locked first, so every check after it
        reads settled numbers and the decision cannot be overtaken between
        looking and writing.
        """
        moment = now()

        sale = self.holds.sale_for_product(payload.sale_product_id)
        if sale is None:
            raise SaleNotFound

        # Checked before the lock too, so a closed sale never queues behind live
        # traffic. Re-checked under it below, in case the window closes meanwhile.
        state = sale.status_at(moment)
        if state != "ACTIVE":
            raise SaleNotRunning(state)

        entry = self.holds.lock_sale_product(payload.sale_product_id)
        if entry is None:
            raise SaleNotFound

        # From here on nobody else can touch this item's counters.
        moment = now()
        state = sale.status_at(moment)
        if state != "ACTIVE":
            raise SaleNotRunning(state)

        self._release_expired_on(entry, moment)

        already = self.holds.quantity_held_by(user.id, entry.id, now=moment)
        if already + payload.quantity > entry.max_per_user:
            raise PurchaseLimitReached(entry.max_per_user, already)

        if payload.quantity > entry.available_quantity:
            raise NotEnoughLeft(entry.available_quantity)

        entry.reserved_quantity += payload.quantity
        hold = Reservation(
            user_id=user.id,
            flash_sale_product_id=entry.id,
            quantity=payload.quantity,
            status=ReservationStatus.ACTIVE,
            expires_at=moment + timedelta(minutes=get_settings().reservation_minutes),
        )
        self.db.add(hold)

        try:
            self.db.commit()
        except IntegrityError:
            # The constraint is the last word. If application arithmetic ever
            # let a hold through that the row cannot support, nothing is written.
            self.db.rollback()
            raise NotEnoughLeft(0) from None

        return self.read(hold.id, user)

    def cancel(self, reservation_id: uuid.UUID, user: User) -> Hold:
        """Let a hold go early and hand its stock straight back."""
        hold = self.holds.get(reservation_id)
        if hold is None or hold.user_id != user.id:
            raise ReservationNotFound

        # Locked before the counter is touched, so a cancel and an expiry sweep
        # racing on the same hold cannot both return the same units.
        entry = self.holds.lock_sale_product(hold.flash_sale_product_id)
        moment = now()
        self.db.refresh(hold)

        live = self._status_at(hold, moment)
        if live != "ACTIVE":
            # Time ran out while they were deciding. The row is corrected to say
            # so, and the stock goes back either way.
            if hold.status is ReservationStatus.ACTIVE:
                self._expire(hold, entry)
                self.db.commit()
            raise ReservationNotActive(live)

        hold.status = ReservationStatus.CANCELLED
        if entry is not None:
            entry.reserved_quantity -= hold.quantity
        self.db.commit()
        return self.read(hold.id, user)

    # Expiry

    def _expire(self, hold: Reservation, entry) -> None:
        """Mark one hold expired and give its units back exactly once."""
        hold.status = ReservationStatus.EXPIRED
        if entry is not None:
            entry.reserved_quantity -= hold.quantity

    def _release_expired_on(self, entry, moment: datetime) -> None:
        """Reclaim this item's dead holds while the row is already locked.

        Without this, stock abandoned by people who never checked out would stay
        unavailable until a sweep ran. Doing it here means the next person to
        reach for the item collects it themselves, at the moment it matters.
        """
        for hold in entry.reservations:
            if hold.status is ReservationStatus.ACTIVE and hold.expires_at <= moment:
                self._expire(hold, entry)

    def sweep(self) -> int:
        """Tidy up holds nobody came back for.

        Purely housekeeping: the numbers are already correct without it, because
        every read discounts holds the clock has passed and every write reclaims
        them under the lock. This just stops EXPIRED rows accumulating unmarked.
        """
        moment = now()
        dead = self.holds.expired_still_holding(moment)
        for hold in dead:
            entry = self.holds.lock_sale_product(hold.flash_sale_product_id)
            self._expire(hold, entry)
        if dead:
            self.db.commit()
        return len(dead)
