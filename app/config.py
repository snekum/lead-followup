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
    environment: str = "development"
    log_level: str = "INFO"
    # IANA timezone used for cadence scheduling / quiet hours.
    timezone: str = "Asia/Kolkata"

    # Infra
    database_url: str = "postgresql+psycopg2://saarthi:saarthi@localhost:5432/saarthi"
    redis_url: str = "redis://localhost:6379/0"

    # WhatsApp provider: "mock" (offline) | "meta" (Cloud API, added in M2)
    whatsapp_provider: str = "mock"

    # Cadence quiet hours (local hour, 24h). No outbound sends in [start, end).
    quiet_hours_start: int = 21
    quiet_hours_end: int = 9


@lru_cache
def get_settings() -> Settings:
    return Settings()
