from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = ""
    migration_database_url: str = ""
    cors_origins: list[str] = ["http://localhost:3000"]
    environment: str = "development"

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
