import uuid
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import (
    ProductNotFound,
    ReminderNotFound,
    SaleAlreadyFinished,
    SaleNotFound,
    SavedItemNotFound,
)
from app.models import SaleReminder, SavedProduct, User
from app.repositories.saved import SavedRepository
from app.schemas.saved import Reminder, SavedItem, Waiting


def now() -> datetime:
    return datetime.now(UTC)


class SavedService:
    """What a shopper marks before a sale opens.

    Neither a saved product nor a reminder holds stock or promises anything.
    They exist so the time before a sale is worth spending: mark what you want,
    and be shown it when the doors open.

    Both are idempotent on purpose. Saving something twice is the same as saving
    it once, so a second tap, a double submit, or two tabs all settle the same
    way rather than raising an error at someone who did nothing wrong.
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self.saved = SavedRepository(db)

    # Saved products

    def mine(self, user: User) -> list[SavedItem]:
        rows = self.saved.saved_for(user.id)
        if not rows:
            return []

        moment = now()
        in_sales = self.saved.live_sale_entries({row.product_id for row in rows}, now=moment)

        items = []
        for row in rows:
            product = row.product
            item = SavedItem(
                id=row.id,
                product_id=product.id,
                product_name=product.name,
                product_slug=product.slug,
                image_url=product.image_url,
                brand=product.brand,
                normal_price=product.base_price,
                saved_at=row.created_at,
            )

            found = in_sales.get(product.id)
            if found is not None:
                entry, sale = found
                item.sale_id = sale.id
                item.sale_name = sale.name
                item.sale_status = sale.status_at(moment)
                item.sale_price = entry.sale_price
                item.sale_product_id = entry.id
                item.starts_at = sale.start_time
                # Only meaningful once the doors are open; before that it is
                # just the allocation, which is not what "left" means.
                if sale.is_running_at(moment):
                    item.available_quantity = entry.available_quantity
            items.append(item)

        return items

    def save(self, product_id: uuid.UUID, user: User) -> SavedItem:
        product = self.saved.product(product_id)
        if product is None or not product.is_active:
            raise ProductNotFound

        existing = self.saved.saved_one(user.id, product_id)
        if existing is None:
            self.db.add(SavedProduct(user_id=user.id, product_id=product_id))
            try:
                self.db.commit()
            except IntegrityError:
                # Two tabs saving at once; the unique pair decides and both are
                # answered with the same saved item.
                self.db.rollback()

        return self._one(product_id, user)

    def forget(self, product_id: uuid.UUID, user: User) -> None:
        existing = self.saved.saved_one(user.id, product_id)
        if existing is None:
            raise SavedItemNotFound
        self.db.delete(existing)
        self.db.commit()

    def _one(self, product_id: uuid.UUID, user: User) -> SavedItem:
        for item in self.mine(user):
            if item.product_id == product_id:
                return item
        raise SavedItemNotFound

    def saved_ids(self, user: User) -> set[uuid.UUID]:
        """Which products this person has saved, for marking them on a listing."""
        return self.saved.saved_product_ids(user.id)

    # Reminders

    def describe_reminder(
        self, reminder: SaleReminder, user: User, at: datetime | None = None
    ) -> Reminder:
        moment = at or now()
        sale = reminder.flash_sale
        return Reminder(
            id=reminder.id,
            sale_id=sale.id,
            sale_name=sale.name,
            description=sale.description,
            starts_at=sale.start_time,
            ends_at=sale.end_time,
            status=sale.status_at(moment),
            item_count=len(sale.sale_products),
            saved_in_sale=self.saved.saved_products_in_sale(user.id, sale.id),
        )

    def my_reminders(self, user: User) -> list[Reminder]:
        """What is coming, soonest first. Finished sales are dropped."""
        moment = now()
        live = [
            reminder
            for reminder in self.saved.reminders_for(user.id)
            if reminder.flash_sale.end_time > moment
        ]
        described = [self.describe_reminder(r, user, moment) for r in live]
        return sorted(described, key=lambda r: r.starts_at)

    def remind_me(self, sale_id: uuid.UUID, user: User) -> Reminder:
        sale = self.saved.sale(sale_id)
        if sale is None:
            raise SaleNotFound
        if sale.end_time <= now():
            # Nothing to come back for.
            raise SaleAlreadyFinished

        existing = self.saved.reminder_one(user.id, sale_id)
        if existing is None:
            self.db.add(SaleReminder(user_id=user.id, flash_sale_id=sale_id))
            try:
                self.db.commit()
            except IntegrityError:
                self.db.rollback()
            existing = self.saved.reminder_one(user.id, sale_id)
            if existing is None:
                raise ReminderNotFound

        return self.describe_reminder(existing, user)

    def forget_sale(self, sale_id: uuid.UUID, user: User) -> None:
        existing = self.saved.reminder_one(user.id, sale_id)
        if existing is None:
            raise ReminderNotFound
        self.db.delete(existing)
        self.db.commit()

    def reminded_ids(self, user: User) -> set[uuid.UUID]:
        return self.saved.reminded_sale_ids(user.id)

    # What to show on arrival

    def waiting_for(self, user: User) -> Waiting:
        """The small summary every page asks for.

        A sale they marked that is running now is the whole reason reminders
        exist, so it is picked out from the rest.
        """
        moment = now()
        reminders = self.my_reminders(user)

        open_now = next((r for r in reminders if r.status == "ACTIVE"), None)
        opening_next = next((r for r in reminders if r.status == "UPCOMING"), None)

        return Waiting(
            saved_count=self.saved.count_saved(user.id),
            reminder_count=self.saved.count_reminders(user.id, unfinished_after=moment),
            open_now=open_now,
            opening_next=opening_next,
        )
