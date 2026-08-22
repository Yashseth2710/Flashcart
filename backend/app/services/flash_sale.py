import uuid
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import (
    AlreadyInTheSale,
    NotEnoughStockToAllocate,
    SaleAlreadyStarted,
    SaleItemNotFound,
    SaleNotFound,
    StockIsSpokenFor,
    VariantNotFound,
)
from app.models import FlashSale, FlashSaleProduct, User
from app.repositories.flash_sale import FlashSaleRepository
from app.schemas.flash_sale import (
    SaleDetail,
    SaleItem,
    SaleItemWrite,
    SaleSummary,
    SaleWrite,
)


def now() -> datetime:
    return datetime.now(UTC)


class FlashSaleService:
    """Sales, and the stock they hold.

    Allocating to a sale moves units out of the warehouse pool rather than
    pointing at them: the warehouse count goes down, the sale gets its own. That
    way the shop cannot sell stock a sale has already promised, and reserving
    during the sale touches one row instead of two.
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self.sales = FlashSaleRepository(db)

    # Reading

    def summarise(self, sale: FlashSale, at: datetime | None = None) -> SaleSummary:
        moment = at or now()
        return SaleSummary(
            id=sale.id,
            name=sale.name,
            description=sale.description,
            start_time=sale.start_time,
            end_time=sale.end_time,
            status=sale.status_at(moment),
            item_count=len(sale.sale_products),
        )

    def describe(self, sale: FlashSale, at: datetime | None = None) -> SaleDetail:
        moment = at or now()
        summary = self.summarise(sale, moment)
        return SaleDetail(
            **summary.model_dump(),
            items=[self._item(entry) for entry in sale.sale_products],
        )

    def _item(self, entry: FlashSaleProduct) -> SaleItem:
        variant = entry.variant
        product = variant.product
        return SaleItem(
            id=entry.id,
            variant_id=variant.id,
            product_name=product.name,
            product_slug=product.slug,
            image_url=product.image_url,
            sku=variant.sku,
            normal_price=variant.price,
            sale_price=entry.sale_price,
            allocated_quantity=entry.allocated_quantity,
            available_quantity=entry.available_quantity,
            max_per_user=entry.max_per_user,
        )

    def upcoming_and_running(self) -> list[SaleDetail]:
        """What a shopper cares about: on now, or coming. Finished sales are gone."""
        moment = now()
        return [self.describe(sale, moment) for sale in self.sales.listing(ended_before=moment)]

    def everything(self) -> list[SaleSummary]:
        moment = now()
        return [self.summarise(sale, moment) for sale in self.sales.all_sales()]

    def read(self, sale_id: uuid.UUID) -> SaleDetail:
        sale = self.sales.get(sale_id)
        if sale is None:
            raise SaleNotFound
        return self.describe(sale)

    def running_now(self) -> SaleDetail | None:
        moment = now()
        for sale in self.sales.listing(ended_before=moment):
            if sale.is_running_at(moment):
                return self.describe(sale, moment)
        return None

    # Writing

    def create(self, payload: SaleWrite, creator: User) -> SaleDetail:
        sale = FlashSale(
            name=payload.name.strip(),
            description=(payload.description or "").strip() or None,
            start_time=payload.start_time,
            end_time=payload.end_time,
            created_by=creator.id,
        )
        self.sales.add(sale)
        self.db.commit()
        return self.read(sale.id)

    def add_item(self, sale_id: uuid.UUID, payload: SaleItemWrite) -> SaleDetail:
        sale = self.sales.get(sale_id)
        if sale is None:
            raise SaleNotFound
        if sale.status_at(now()) != "UPCOMING":
            raise SaleAlreadyStarted

        pair = self.sales.variant_with_stock(payload.variant_id)
        if pair is None:
            raise VariantNotFound
        _, inventory = pair

        if self.sales.item_for_variant(sale_id, payload.variant_id) is not None:
            raise AlreadyInTheSale

        if payload.allocated_quantity > inventory.available_quantity:
            raise NotEnoughStockToAllocate(inventory.available_quantity)

        # The warehouse holds the units on the sale's behalf until it ends.
        inventory.reserved_quantity += payload.allocated_quantity
        self.db.add(
            FlashSaleProduct(
                flash_sale_id=sale_id,
                variant_id=payload.variant_id,
                sale_price=payload.sale_price,
                allocated_quantity=payload.allocated_quantity,
                max_per_user=payload.max_per_user,
            )
        )
        try:
            self.db.commit()
        except IntegrityError:
            # Two admins adding the same product at once; the unique index decides.
            self.db.rollback()
            raise AlreadyInTheSale from None
        return self.read(sale_id)

    def remove_item(self, sale_id: uuid.UUID, item_id: uuid.UUID) -> SaleDetail:
        sale = self.sales.get(sale_id)
        if sale is None:
            raise SaleNotFound

        entry = self.sales.item(item_id)
        if entry is None or entry.flash_sale_id != sale_id:
            raise SaleItemNotFound

        committed = entry.reserved_quantity + entry.sold_quantity
        if committed > 0:
            raise StockIsSpokenFor(committed)

        pair = self.sales.variant_with_stock(entry.variant_id)
        if pair is not None:
            _, inventory = pair
            # Hand the untouched allocation back to the warehouse.
            inventory.reserved_quantity -= entry.allocated_quantity

        self.db.delete(entry)
        self.db.commit()
        return self.read(sale_id)

    def cancel(self, sale_id: uuid.UUID) -> None:
        """Deleting a sale returns whatever nobody claimed to the warehouse."""
        sale = self.sales.get(sale_id)
        if sale is None:
            raise SaleNotFound

        for entry in sale.sale_products:
            committed = entry.reserved_quantity + entry.sold_quantity
            if committed > 0:
                raise StockIsSpokenFor(committed)

            pair = self.sales.variant_with_stock(entry.variant_id)
            if pair is not None:
                _, inventory = pair
                inventory.reserved_quantity -= entry.allocated_quantity

        self.db.delete(sale)
        self.db.commit()
