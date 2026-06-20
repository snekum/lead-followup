"""Minimal inbound handling: persist the reply, honor opt-out, stop the cadence.

The assistant that actually *answers* inbound messages arrives in M3; this layer
covers the cadence rules (stop-on-reply, opt-out) that belong with M2.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Event, Lead, Message
from app.domain.enums import (
    LeadStatus,
    MessageDirection,
    MessageKind,
    MessageStatus,
)
from app.domain.lead_state import can_transition
from app.services.cadence import cancel_pending_touches
from app.services.phone import PhoneError, normalize_phone

_OPT_OUT_KEYWORDS = (
    "stop",
    "unsubscribe",
    "cancel",
    "बंद",
    "रोको",
    "रुको",
    "ఆపండి",
    "ఆపు",
    "వద్దు",
)


def is_opt_out(text: str) -> bool:
    lowered = text.strip().lower()
    return any(keyword in lowered for keyword in _OPT_OUT_KEYWORDS)


def _find_lead(session: Session, phone: str) -> Lead | None:
    try:
        normalized = normalize_phone(phone)
    except PhoneError:
        normalized = phone
    return session.scalar(select(Lead).where(Lead.phone == normalized))


def handle_inbound(
    session: Session,
    *,
    phone: str,
    text: str,
    provider_message_id: str | None = None,
) -> Lead | None:
    """Record an inbound message and apply opt-out / stop-on-reply rules."""
    lead = _find_lead(session, phone)
    if lead is None:
        return None  # unknown sender; ignored in the pilot

    session.add(
        Message(
            lead_id=lead.id,
            direction=MessageDirection.INBOUND,
            kind=MessageKind.TEXT,
            body=text,
            status=MessageStatus.DELIVERED,
            provider_message_id=provider_message_id,
        )
    )

    if is_opt_out(text):
        lead.opt_out = True
        if can_transition(lead.status, LeadStatus.OPTED_OUT):
            lead.status = LeadStatus.OPTED_OUT
        cancel_pending_touches(session, lead)
        session.add(Event(lead_id=lead.id, type="opt_out"))
    else:
        # Stop-on-reply: pause automated nudges and mark the lead engaged.
        if can_transition(lead.status, LeadStatus.ENGAGED):
            lead.status = LeadStatus.ENGAGED
        cancel_pending_touches(session, lead)
        session.add(
            Event(lead_id=lead.id, type="inbound_reply", data={"text": text[:200]})
        )

    session.commit()
    return lead
