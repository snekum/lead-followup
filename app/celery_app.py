"""Celery application. The nudge-cadence tasks land here in M2."""
from __future__ import annotations

from celery import Celery

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "saarthi",
    broker=settings.redis_url,
    backend=settings.redis_url,
)
celery_app.conf.timezone = settings.timezone
celery_app.conf.task_track_started = True


@celery_app.task(name="saarthi.ping")
def ping() -> str:
    """Trivial task to confirm the worker is wired up."""
    return "pong"
