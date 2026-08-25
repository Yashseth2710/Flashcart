from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = ""
    migration_database_url: str = ""
    cors_origins: list[str] = ["http://localhost:3000"]
    jwt_secret: str = "development-only-not-for-deployment"
    access_token_minutes: int = 60 * 24
    cookie_name: str = "flashcart_session"
    cookie_secure: bool = False
    environment: str = "development"
    # How long a hold lasts. Long enough to finish checking out, short enough
    # that an abandoned basket does not sit on stock others are waiting for.
    reservation_minutes: int = 10

    # Attempts allowed per minute before a caller is asked to slow down.
    #
    # A flash sale rewards clicking fast, so these are set well above what a
    # determined shopper produces by hand and only bite on something scripted.
    # Holds and checkout are counted per account; the sign-in pair is counted
    # per address, because someone guessing passwords has no account yet.
    holds_per_minute: int = 30
    checkouts_per_minute: int = 20
    logins_per_minute: int = 10
    registrations_per_minute: int = 5
    marks_per_minute: int = 60
    # Windows older than this are no longer read, so they are swept away.
    request_count_retention_minutes: int = 60

    # How many database connections the app may hold at once.
    #
    # Everyone reaching for the same item queues on one row lock, and a request
    # waiting its turn is holding a connection the whole time. The pool has to
    # be deep enough for the queue, or people are turned away for want of a
    # connection rather than for want of stock.
    pool_size: int = 20
    pool_overflow: int = 30
    # How long to wait for one before giving up. Kept under the reservation
    # window so a request fails cleanly rather than being killed mid-transaction.
    pool_wait_seconds: int = 20

    @model_validator(mode="after")
    def _refuse_to_run_unsigned(self) -> "Settings":
        """A blank secret would sign tokens anyone could forge."""
        if self.environment != "development" and not self.jwt_secret:
            raise ValueError("JWT_SECRET must be set outside development")
        return self

    @property
    def database_configured(self) -> bool:
        return bool(self.database_url)

    @property
    def alembic_url(self) -> str:
        """Migrations prefer a direct connection; a transaction pooler can mangle DDL."""
        return self.migration_database_url or self.database_url


@lru_cache
def get_settings() -> Settings:
    return Settings()
