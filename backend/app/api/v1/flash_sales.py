import uuid

from fastapi import APIRouter

from app.core.dependencies import DbSession
from app.schemas.flash_sale import SaleDetail
from app.services.flash_sale import FlashSaleService

router = APIRouter(prefix="/flash-sales", tags=["flash sales"])


@router.get("", response_model=list[SaleDetail])
def list_sales(db: DbSession) -> list[SaleDetail]:
    """What is on now and what is coming. Finished sales are not shown."""
    return FlashSaleService(db).upcoming_and_running()


@router.get("/running", response_model=SaleDetail | None)
def read_running_sale(db: DbSession) -> SaleDetail | None:
    return FlashSaleService(db).running_now()


@router.get("/{sale_id}", response_model=SaleDetail)
def read_sale(sale_id: uuid.UUID, db: DbSession) -> SaleDetail:
    return FlashSaleService(db).read(sale_id)
