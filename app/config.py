"""Application settings, loaded from environment / .env via pydantic-settings."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # App
    app_name: str = "Saarthi Lead Follow-up"
    # Dealership display name used in outbound message templates.
    dealership_name: str = "Tata Motors Hyderabad"
    environment: str = "development"
    log_level: str = "INFO"
    # IANA timezone used for cadence scheduling / quiet hours.
    timezone: str = "Asia/Kolkata"

    # Infra
    database_url: str = "postgresql+psycopg2://saarthi:saarthi@localhost:5432/saarthi"
    redis_url: str = "redis://localhost:6379/0"

    # WhatsApp provider: "mock" (offline) | "meta" (Cloud API)
    whatsapp_provider: str = "mock"

    # Meta WhatsApp Cloud API (used when whatsapp_provider == "meta")
    meta_access_token: str = ""
    meta_phone_number_id: str = ""
    meta_api_version: str = "v21.0"
    meta_verify_token: str = "saarthi-verify"
    meta_app_secret: str = ""

    # Cadence
    cadence_enabled: bool = True
    # Cadence quiet hours (local hour, 24h). No outbound sends in [start, end).
    quiet_hours_start: int = 21
    quiet_hours_end: int = 9


@lru_cache
def get_settings() -> Settings:
    return Settings()
