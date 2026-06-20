from sqlalchemy import select

from app.db.models import Lead, Message, ScheduledTouch
from app.domain.enums import LeadStatus, MessageDirection, TouchStatus
from app.services.cadence import schedule_cadence
from app.services.inbound import handle_inbound, is_opt_out


def _lead_with_cadence(session, status=LeadStatus.CONTACTED):
    lead = Lead(name="Ravi", phone="+919876543210", status=status)
    session.add(lead)
    session.flush()
    schedule_cadence(session, lead)
    session.commit()
    return lead


def test_reply_stops_cadence(db_session):
    lead = _lead_with_cadence(db_session)
    # inbound "from" comes without a leading +, like Meta sends it
    result = handle_inbound(db_session, phone="919876543210", text="Yes, interested!")

    assert result is not None
    db_session.refresh(lead)
    assert lead.status == LeadStatus.ENGAGED
    pending = db_session.scalars(
        select(ScheduledTouch).where(ScheduledTouch.status == TouchStatus.PENDING)
    ).all()
    assert pending == []
    inbound = db_session.scalar(
        select(Message).where(Message.direction == MessageDirection.INBOUND)
    )
    assert inbound is not None
    assert inbound.body == "Yes, interested!"


def test_opt_out_sets_status(db_session):
    lead = _lead_with_cadence(db_session)
    handle_inbound(db_session, phone="+919876543210", text="STOP")

    db_session.refresh(lead)
    assert lead.opt_out is True
    assert lead.status == LeadStatus.OPTED_OUT


def test_unknown_sender_ignored(db_session):
    assert handle_inbound(db_session, phone="+910000000000", text="hi") is None


def test_is_opt_out():
    assert is_opt_out("STOP")
    assert is_opt_out("Please stop messaging")
    assert not is_opt_out("I am interested")
