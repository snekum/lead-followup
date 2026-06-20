import datetime as dt

from sqlalchemy import select

from app.db.models import Lead, Message, ScheduledTouch
from app.domain.enums import LeadStatus, MessageStatus, TouchStatus
from app.providers.whatsapp.base import SendResult
from app.services.cadence import (
    CADENCE,
    cancel_pending_touches,
    is_quiet_hour,
    process_due_touches,
    schedule_cadence,
)

UTC = dt.UTC


class RecordingProvider:
    def __init__(self) -> None:
        self.sent: list[tuple] = []

    def send_template(self, to, template_name, language, variables=None):
        self.sent.append((to, template_name, language, variables))
        return SendResult(provider_message_id=f"mock-{len(self.sent)}")

    def send_text(self, to, body):
        return SendResult(provider_message_id="mock-text")


def _make_lead(session, *, status=LeadStatus.NEW, opt_out=False):
    lead = Lead(
        name="Ravi",
        phone="+919876543210",
        interested_model="Nexon",
        status=status,
        opt_out=opt_out,
    )
    session.add(lead)
    session.flush()
    return lead


def _noon_utc():  # 06:30 UTC == 12:00 IST -> not quiet
    return dt.datetime(2026, 6, 19, 6, 30, tzinfo=UTC)


def _late_ist():  # 18:00 UTC == 23:30 IST -> quiet
    return dt.datetime(2026, 6, 19, 18, 0, tzinfo=UTC)


def _due_touch(session, lead):
    session.add(
        ScheduledTouch(
            lead_id=lead.id,
            step_key="day0_thankyou",
            scheduled_for=dt.datetime(2026, 1, 1, tzinfo=UTC),
            status=TouchStatus.PENDING,
        )
    )
    session.commit()


def test_schedule_creates_touches(db_session):
    lead = _make_lead(db_session)
    schedule_cadence(db_session, lead)
    db_session.commit()
    touches = db_session.scalars(select(ScheduledTouch)).all()
    assert len(touches) == len(CADENCE)
    assert all(t.status == TouchStatus.PENDING for t in touches)


def test_quiet_hours_helper():
    assert is_quiet_hour(_late_ist(), tz="Asia/Kolkata", start=21, end=9)
    assert not is_quiet_hour(_noon_utc(), tz="Asia/Kolkata", start=21, end=9)


def test_process_sends_due_touch(db_session):
    lead = _make_lead(db_session)
    _due_touch(db_session, lead)
    provider = RecordingProvider()

    summary = process_due_touches(db_session, provider, now=_noon_utc())

    assert summary["sent"] == 1
    assert len(provider.sent) == 1
    db_session.refresh(lead)
    assert lead.status == LeadStatus.CONTACTED
    message = db_session.scalar(select(Message))
    assert message is not None
    assert message.status == MessageStatus.SENT
    assert message.provider_message_id == "mock-1"


def test_quiet_hours_blocks_send(db_session):
    lead = _make_lead(db_session)
    _due_touch(db_session, lead)

    summary = process_due_touches(db_session, RecordingProvider(), now=_late_ist())

    assert summary["sent"] == 0
    touch = db_session.scalar(select(ScheduledTouch))
    assert touch.status == TouchStatus.PENDING  # left for the next window


def test_opt_out_cancels_touch(db_session):
    lead = _make_lead(db_session, opt_out=True)
    _due_touch(db_session, lead)

    summary = process_due_touches(db_session, RecordingProvider(), now=_noon_utc())

    assert summary["sent"] == 0
    assert summary["cancelled"] == 1


def test_cancel_pending(db_session):
    lead = _make_lead(db_session)
    schedule_cadence(db_session, lead)
    db_session.commit()
    cancelled = cancel_pending_touches(db_session, lead)
    db_session.commit()
    assert cancelled == len(CADENCE)
