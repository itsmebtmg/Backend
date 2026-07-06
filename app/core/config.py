from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "local"
    app_name: str = "Solyra API"
    api_base_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:3000"

    database_url: str = "postgresql+asyncpg://solyra:solyra@localhost:5432/solyra"
    alembic_database_url: str = "postgresql://solyra:solyra@localhost:5432/solyra"

    cors_origins: list[str] = ["http://localhost:3000"]

    google_sheets_webhook_url: str | None = None
    google_sheets_webhook_secret: str | None = None

    meta_pixel_id: str | None = None
    meta_access_token: str | None = None
    meta_test_event_code: str | None = None

    tiktok_pixel_code: str | None = None
    tiktok_access_token: str | None = None
    tiktok_test_event_code: str | None = None

    snap_pixel_id: str | None = None
    snap_access_token: str | None = None
    snap_test_event_code: str | None = None

    enable_capi: bool = True
    enable_google_sheets: bool = True
    tracking_debug: bool = False

    rate_limit_orders_per_ip_per_hour: int = 10
    rate_limit_orders_per_phone_per_day: int = 3

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
