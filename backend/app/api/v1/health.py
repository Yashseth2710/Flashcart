from fastapi import APIRouter
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import get_settings
from app.db.session import get_engine
from app.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


def check_database() -> str:
    settings = get_settings()
    if not settings.database_configured:
        return "not_configured"
    try:
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return "unreachable"
    return "connected"


@router.get("/health", response_model=HealthResponse)
def read_health() -> HealthResponse:
    database = check_database()
    return HealthResponse(
        status="ok" if database == "connected" else "degraded",
        environment=get_settings().environment,
        database=database,
    )
