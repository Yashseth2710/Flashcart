from fastapi import APIRouter

from app.api.v1 import (
    admin,
    auth,
    flash_sales,
    health,
    orders,
    products,
    reservations,
    saved,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(products.router)
api_router.include_router(flash_sales.router)
api_router.include_router(reservations.router)
api_router.include_router(orders.router)
api_router.include_router(saved.router)
api_router.include_router(admin.router)
