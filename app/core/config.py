from functools import lru_cache
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "local"
    app_name: str = "Solyra API"
    api_base_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:3000"

    database_url: str = "postgresql+asyncpg://solyra:solyra@localhost:5432/solyra"
    alembic_database_url: str = "postgresql://solyra:solyra@localhost:5432/solyra"

    # NoDecode stops pydantic-settings from trying to JSON-parse this env var
    # before our validator runs. Without it, a raw comma-separated string (or
    # one accidentally wrapped in brackets, e.g. "[a,b]") is invalid JSON and
    # crashes the app at startup instead of being parsed below.
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:3000"]

    google_sheets_webhook_url: str | None = None
    # Shared secret the Google Apps Script "Status" onEdit trigger must send
    # back to /v1/orders/sheet-status so anyone with the endpoint URL can't
    # tamper with order statuses.
    order_webhook_secret: str | None = None

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
    enable_n8n_whatsapp: bool = False
    n8n_order_webhook_url: str | None = None
    tracking_debug: bool = False

    rate_limit_orders_per_ip_per_hour: int = 10
    rate_limit_orders_per_phone_per_day: int = 3

    # --- Admin dashboard -------------------------------------------------
    admin_username: str = "admin"
    admin_password: str = "change-me"
    jwt_secret_key: str = "insecure-dev-secret-change-me"
    jwt_expire_minutes: int = 60 * 12
    admin_cookie_name: str = "solyra_admin_session"
    admin_cookie_secure: bool = True

    # --- Geo / VPN detection (MaxMind GeoIP2 web service) ----------------
    maxmind_account_id: str | None = None
    maxmind_license_key: str | None = None
    geo_cache_ttl_seconds: int = 3600

    # --- Shipping / delivery ----------------------------------------------
    # No provider is wired in yet — delivery_status is edited manually by an
    # admin. Fill these in once the shipping company's API is available and
    # implement a matching provider in app/services/shipping.py.
    shipping_provider: str = "manual"
    shipping_api_base_url: str | None = None
    shipping_api_key: str | None = None

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            # tolerate accidental wrapping like "[a,b]" or quotes/whitespace
            cleaned = value.strip().strip("[]")
            return [
                item.strip().strip("'\"")
                for item in cleaned.split(",")
                if item.strip().strip("'\"")
            ]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
