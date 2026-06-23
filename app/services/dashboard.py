"""Read-side aggregations for the manager dashboard."""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Event, Feedback, Lead, Message
from app.domain.enums import LeadStatus, MessageDirection

# Order statuses follow through the funnel.
FUNNEL_ORDER = [
    LeadStatus.NEW,
    LeadStatus.CONTACTED,
    LeadStatus.ENGAGED,
    LeadStatus.TEST_DRIVE_REQUESTED,
    LeadStatus.FEEDBACK_GIVEN,
    LeadStatus.HANDED_OFF,
    LeadStatus.WON,
    LeadStatus.LOST,
    LeadStatus.OPTED_OUT,
    LeadStatus.UNREACHABLE,
]


def status_counts(session: Session) -> dict[LeadStatus, int]:
    counts = {status: 0 for status in LeadStatus}
    for row in session.execute(
        select(Lead.status, func.count()).group_by(Lead.status)
    ).all():
        counts[row[0]] = row[1]
    return counts


def metrics(session: Session) -> dict[str, object]:
    counts = status_counts(session)
    total = sum(counts.values())
    contacted = total - counts[LeadStatus.NEW]
    engaged = (
        session.scalar(
            select(func.count(func.distinct(Message.lead_id))).where(
                Message.direction == MessageDirection.INBOUND
            )
        )
        or 0
    )
    test_drives = (
        session.scalar(
            select(func.count(func.distinct(Event.lead_id))).where(
                Event.type == "test_drive_requested"
            )
        )
        or 0
    )
    feedback_count = session.scalar(select(func.count()).select_from(Feedback)) or 0
    return {
        "total": total,
        "contacted": contacted,
        "engaged": engaged,
        "reply_rate": round(100 * engaged / contacted) if contacted else 0,
        "test_drives": test_drives,
        "handoffs": counts[LeadStatus.HANDED_OFF],
        "opted_out": counts[LeadStatus.OPTED_OUT],
        "feedback": feedback_count,
    }


def funnel(session: Session) -> list[tuple[LeadStatus, int]]:
    counts = status_counts(session)
    return [(status, counts[status]) for status in FUNNEL_ORDER]


def needs_human(session: Session, limit: int = 50) -> list[Lead]:
    return list(
        session.scalars(
            select(Lead)
            .where(Lead.status == LeadStatus.HANDED_OFF, Lead.opt_out.is_(False))
            .order_by(Lead.updated_at.desc())
            .limit(limit)
        )
    )


def recent_leads(session: Session, limit: int = 25) -> list[Lead]:
    return list(
        session.scalars(
            select(Lead).order_by(Lead.created_at.desc()).limit(limit)
        )
    )


@dataclass
class LeadDetail:
    lead: Lead
    messages: list[Message]
    events: list[Event]
    feedback: list[Feedback]


def lead_detail(session: Session, lead_id: int) -> LeadDetail | None:
    lead = session.get(Lead, lead_id)
    if lead is None:
        return None
    messages = list(
        session.scalars(
            select(Message).where(Message.lead_id == lead_id).order_by(Message.created_at)
        )
    )
    events = list(
        session.scalars(
            select(Event).where(Event.lead_id == lead_id).order_by(Event.created_at)
        )
    )
    feedback = list(
        session.scalars(
            select(Feedback)
            .where(Feedback.lead_id == lead_id)
            .order_by(Feedback.created_at)
        )
    )
    return LeadDetail(lead=lead, messages=messages, events=events, feedback=feedback)
