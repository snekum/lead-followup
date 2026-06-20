"""Celery tasks. Beat triggers the cadence sweep; see app/celery_app.py."""
from __future__ import annotations

from app.celery_app import celery_app
from app.db.session import SessionLocal
from app.providers.whatsapp.factory import get_whatsapp_provider
from app.services.cadence import process_due_touches


@celery_app.task(name="saarthi.process_due_touches")
def process_due_touches_task() -> dict[str, int]:
    with SessionLocal() as session:
        provider = get_whatsapp_provider()
        return process_due_touches(session, provider)
