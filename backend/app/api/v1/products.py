from typing import Annotated

from fastapi import APIRouter, Query

from app.core.dependencies import DbSession
from app.models import Product
from app.schemas.catalogue import ProductDetail, ProductPage
from app.services.catalogue import CatalogueService

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=ProductPage)
def browse_products(
    db: DbSession,
    search: Annotated[str | None, Query(max_length=120)] = None,
    category: Annotated[str | None, Query(max_length=80)] = None,
    limit: Annotated[int, Query(ge=1, le=48)] = 24,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ProductPage:
    items, total = CatalogueService(db).browse(
        term=search, category=category, limit=limit, offset=offset
    )
    return ProductPage(items=items, total=total, limit=limit, offset=offset)


@router.get("/categories", response_model=list[str])
def list_categories(db: DbSession) -> list[str]:
    return CatalogueService(db).products.categories()


@router.get("/{slug}", response_model=ProductDetail)
def read_product(slug: str, db: DbSession) -> Product:
    return CatalogueService(db).read(slug)
