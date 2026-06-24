"""FastAPI application factory."""
from __future__ import annotations

from fastapi import FastAPI

from app.api import dashboard, health, leads, simulator, webhook
from app.config import get_settings
from app.logging_config import configure_logging


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(title=settings.app_name, version="0.0.1")
    app.include_router(health.router)
    app.include_router(leads.router)
    app.include_router(webhook.router)
    app.include_router(dashboard.router)
    app.include_router(simulator.router)
    return app


app = create_app()
