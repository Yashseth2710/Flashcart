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
