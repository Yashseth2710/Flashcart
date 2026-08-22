import uuid
from typing import Annotated

from fastapi import APIRouter, Query, status

from app.core.dependencies import AdminUser, DbSession
from app.models import Product
from app.schemas.catalogue import (
    ProductDetail,
    ProductPage,
    ProductUpdate,
    ProductWrite,
    StockLevel,
    StockWrite,
)
from app.schemas.flash_sale import SaleDetail, SaleItemWrite, SaleSummary, SaleWrite
from app.services.catalogue import CatalogueService
from app.services.flash_sale import FlashSaleService

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/products", response_model=ProductDetail, status_code=status.HTTP_201_CREATED)
def create_product(payload: ProductWrite, db: DbSession, _: AdminUser) -> Product:
    return CatalogueService(db).create(payload)


@router.patch("/products/{product_id}", response_model=ProductDetail)
def update_product(
    product_id: uuid.UUID, payload: ProductUpdate, db: DbSession, _: AdminUser
) -> Product:
    return CatalogueService(db).update(product_id, payload)


@router.get("/products/{product_id}/stock", response_model=list[StockLevel])
def read_stock(product_id: uuid.UUID, db: DbSession, _: AdminUser) -> list[StockLevel]:
    levels = CatalogueService(db).inventory.levels_for_product(product_id)
    return [
        StockLevel(
            variant_id=variant.id,
            sku=variant.sku,
            total_quantity=inventory.total_quantity,
            reserved_quantity=inventory.reserved_quantity,
            sold_quantity=inventory.sold_quantity,
            available_quantity=inventory.available_quantity,
        )
        for variant, inventory in levels
    ]


@router.put("/stock", response_model=StockLevel)
def set_stock(payload: StockWrite, db: DbSession, _: AdminUser) -> StockLevel:
    variant, inventory = CatalogueService(db).set_stock(payload.variant_id, payload.total_quantity)
    return StockLevel(
        variant_id=variant.id,
        sku=variant.sku,
        total_quantity=inventory.total_quantity,
        reserved_quantity=inventory.reserved_quantity,
        sold_quantity=inventory.sold_quantity,
        available_quantity=inventory.available_quantity,
    )


@router.get("/products", response_model=ProductPage)
def list_products_to_manage(
    db: DbSession,
    _: AdminUser,
    search: Annotated[str | None, Query(max_length=120)] = None,
    limit: Annotated[int, Query(ge=1, le=48)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ProductPage:
    """Everything in the shop, hidden products included, newest first."""
    items, total = CatalogueService(db).browse(
        term=search,
        category=None,
        limit=limit,
        offset=offset,
        include_inactive=True,
        newest_first=True,
    )
    return ProductPage(items=items, total=total, limit=limit, offset=offset)


@router.get("/flash-sales", response_model=list[SaleSummary])
def list_all_sales(db: DbSession, _: AdminUser) -> list[SaleSummary]:
    """Every sale, finished ones included, newest first."""
    return FlashSaleService(db).everything()


@router.post("/flash-sales", response_model=SaleDetail, status_code=status.HTTP_201_CREATED)
def create_sale(payload: SaleWrite, db: DbSession, admin: AdminUser) -> SaleDetail:
    return FlashSaleService(db).create(payload, admin)


@router.get("/flash-sales/{sale_id}", response_model=SaleDetail)
def read_sale_to_manage(sale_id: uuid.UUID, db: DbSession, _: AdminUser) -> SaleDetail:
    return FlashSaleService(db).read(sale_id)


@router.post("/flash-sales/{sale_id}/items", response_model=SaleDetail)
def add_sale_item(
    sale_id: uuid.UUID, payload: SaleItemWrite, db: DbSession, _: AdminUser
) -> SaleDetail:
    """Puts a product in the sale, moving its stock out of the warehouse."""
    return FlashSaleService(db).add_item(sale_id, payload)


@router.delete("/flash-sales/{sale_id}/items/{item_id}", response_model=SaleDetail)
def remove_sale_item(
    sale_id: uuid.UUID, item_id: uuid.UUID, db: DbSession, _: AdminUser
) -> SaleDetail:
    return FlashSaleService(db).remove_item(sale_id, item_id)


@router.delete("/flash-sales/{sale_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_sale(sale_id: uuid.UUID, db: DbSession, _: AdminUser) -> None:
    FlashSaleService(db).cancel(sale_id)
