"""Lead operations: create (with dedupe) and guarded status changes."""
from __future__ import annotations

import datetime as dt

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Event, Lead
from app.domain.enums import Language, LeadSource, LeadStatus
from app.domain.lead_state import InvalidTransition, assert_transition
from app.services.cadence import schedule_cadence
from app.services.phone import normalize_phone


class DuplicateLead(Exception):
    """A lead with this phone already exists."""


def create_lead(
    session: Session,
    *,
    name: str,
    phone: str,
    source: LeadSource = LeadSource.FORM,
    interested_model: str | None = None,
    budget: str | None = None,
    visit_date: dt.date | None = None,
    preferred_language: Language = Language.EN,
    location_id: int | None = None,
    notes: str | None = None,
) -> Lead:
    normalized = normalize_phone(phone)
    if session.scalar(select(Lead).where(Lead.phone == normalized)):
        raise DuplicateLead(normalized)

    lead = Lead(
        name=name.strip(),
        phone=normalized,
        source=source,
        interested_model=interested_model,
        budget=budget,
        visit_date=visit_date,
        preferred_language=preferred_language,
        location_id=location_id,
        notes=notes,
    )
    session.add(lead)
    session.flush()
    session.add(
        Event(lead_id=lead.id, type="lead_created", data={"source": source.value})
    )
    schedule_cadence(session, lead)
    session.commit()
    session.refresh(lead)
    return lead


def set_status(
    session: Session, lead: Lead, to: LeadStatus, *, reason: str | None = None
) -> None:
    """Apply a guarded transition and record an event, WITHOUT committing."""
    assert_transition(lead.status, to)
    previous = lead.status
    lead.status = to
    session.add(
        Event(
            lead_id=lead.id,
            type="status_change",
            data={"from": previous.value, "to": to.value, "reason": reason},
        )
    )


def try_set_status(
    session: Session, lead: Lead, to: LeadStatus, *, reason: str | None = None
) -> bool:
    """Like set_status, but returns False instead of raising on an invalid transition."""
    try:
        set_status(session, lead, to, reason=reason)
        return True
    except InvalidTransition:
        return False


def change_status(
    session: Session, lead: Lead, to: LeadStatus, *, reason: str | None = None
) -> Lead:
    """Apply a guarded lifecycle transition and commit."""
    set_status(session, lead, to, reason=reason)
    session.commit()
    session.refresh(lead)
    return lead


def list_leads(
    session: Session,
    *,
    status: LeadStatus | None = None,
    limit: int = 100,
) -> list[Lead]:
    stmt = select(Lead).order_by(Lead.created_at.desc()).limit(limit)
    if status is not None:
        stmt = stmt.where(Lead.status == status)
    return list(session.scalars(stmt))
