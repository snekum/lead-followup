"""Follow-up cadence: schedule nudges, then send the due ones.

The cadence is DB-driven: each planned nudge is a ``ScheduledTouch`` row. A
Celery beat task calls :func:`process_due_touches` every minute; that function
enforces quiet hours, stop-on-reply, and opt-out at send time, so it is safe to
run repeatedly and survives restarts.
"""
from __future__ import annotations

import datetime as dt
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import Lead, Message, ScheduledTouch
from app.domain.enums import (
    LeadStatus,
    MessageDirection,
    MessageKind,
    MessageStatus,
    TouchStatus,
)
from app.providers.whatsapp.base import WhatsAppProvider
from app.services.templates import render_template

# (step_key, day offset from lead creation)
CADENCE: list[tuple[str, int]] = [
    ("day0_thankyou", 0),
    ("day2_modelinfo", 2),
    ("day5_testdrive", 5),
    ("day9_final", 9),
]

# Lead is still in the automated-nudge phase only in these statuses.
_ACTIVE_STATUSES = {LeadStatus.NEW, LeadStatus.CONTACTED, LeadStatus.UNREACHABLE}


def _utcnow() -> dt.datetime:
    return dt.datetime.now(tz=dt.UTC)


def schedule_cadence(session: Session, lead: Lead) -> None:
    """Create the pending touches for a new lead. Caller commits."""
    base = lead.created_at or _utcnow()
    for step_key, offset in CADENCE:
        session.add(
            ScheduledTouch(
                lead_id=lead.id,
                step_key=step_key,
                scheduled_for=base + dt.timedelta(days=offset),
                status=TouchStatus.PENDING,
            )
        )


def cancel_pending_touches(session: Session, lead: Lead) -> int:
    touches = session.scalars(
        select(ScheduledTouch).where(
            ScheduledTouch.lead_id == lead.id,
            ScheduledTouch.status == TouchStatus.PENDING,
        )
    ).all()
    for touch in touches:
        touch.status = TouchStatus.CANCELLED
    return len(touches)


def is_quiet_hour(now: dt.datetime, *, tz: str, start: int, end: int) -> bool:
    """True if local time falls in the no-send window [start, end)."""
    local_hour = now.astimezone(ZoneInfo(tz)).hour
    if start <= end:
        return start <= local_hour < end
    # window wraps midnight, e.g. 21:00 -> 09:00
    return local_hour >= start or local_hour < end


def process_due_touches(
    session: Session,
    provider: WhatsAppProvider,
    *,
    now: dt.datetime | None = None,
) -> dict[str, int]:
    settings = get_settings()
    now = now or _utcnow()
    summary = {"sent": 0, "cancelled": 0, "failed": 0}

    if is_quiet_hour(
        now,
        tz=settings.timezone,
        start=settings.quiet_hours_start,
        end=settings.quiet_hours_end,
    ):
        return summary  # outside the sending window; leave touches pending

    due = session.scalars(
        select(ScheduledTouch)
        .where(
            ScheduledTouch.status == TouchStatus.PENDING,
            ScheduledTouch.scheduled_for <= now,
        )
        .order_by(ScheduledTouch.scheduled_for)
    ).all()

    for touch in due:
        lead = session.get(Lead, touch.lead_id)
        if lead is None:
            touch.status = TouchStatus.SKIPPED
            continue
        # Stop-on-reply / opt-out: the lead has left the nudge phase.
        if lead.opt_out or lead.status not in _ACTIVE_STATUSES:
            touch.status = TouchStatus.CANCELLED
            summary["cancelled"] += 1
            continue

        body = render_template(touch.step_key, lead)
        try:
            result = provider.send_template(
                to=lead.phone,
                template_name=touch.step_key,
                language=lead.preferred_language.value,
                variables=[lead.name, lead.interested_model or "Tata car"],
            )
        except Exception as exc:  # noqa: BLE001 - record any provider failure
            failed = Message(
                lead_id=lead.id,
                direction=MessageDirection.OUTBOUND,
                kind=MessageKind.TEMPLATE,
                template_name=touch.step_key,
                body=body,
                status=MessageStatus.FAILED,
                error=str(exc),
                step_key=touch.step_key,
            )
            session.add(failed)
            session.flush()
            touch.status = TouchStatus.FAILED
            touch.message_id = failed.id
            summary["failed"] += 1
            continue

        message = Message(
            lead_id=lead.id,
            direction=MessageDirection.OUTBOUND,
            kind=MessageKind.TEMPLATE,
            template_name=touch.step_key,
            body=body,
            status=MessageStatus.SENT,
            provider_message_id=result.provider_message_id,
            sent_at=now,
            step_key=touch.step_key,
        )
        session.add(message)
        session.flush()
        touch.status = TouchStatus.SENT
        touch.message_id = message.id
        lead.last_contacted_at = now
        if lead.status == LeadStatus.NEW:
            lead.status = LeadStatus.CONTACTED
        summary["sent"] += 1

    session.commit()
    return summary
