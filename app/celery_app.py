"""Celery application. The nudge-cadence tasks land here in M2."""
from __future__ import annotations

from celery import Celery

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "saarthi",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks"],
)
celery_app.conf.timezone = settings.timezone
celery_app.conf.task_track_started = True

# Beat scans for due nudges every minute; the task itself enforces quiet hours.
celery_app.conf.beat_schedule = {
    "process-due-touches": {
        "task": "saarthi.process_due_touches",
        "schedule": 60.0,
    },
}


@celery_app.task(name="saarthi.ping")
def ping() -> str:
    """Trivial task to confirm the worker is wired up."""
    return "pong"
