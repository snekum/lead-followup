"""FastAPI application factory."""
from __future__ import annotations

from fastapi import FastAPI

from app.api import health
from app.config import get_settings
from app.logging_config import configure_logging


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(title=settings.app_name, version="0.0.1")
    app.include_router(health.router)
    return app


app = create_app()
