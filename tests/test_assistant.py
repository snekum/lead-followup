from sqlalchemy import select

from app.assistant.agent import respond_to_inbound
from app.db.models import Feedback, Lead, Message
from app.domain.enums import LeadStatus, MessageDirection, MessageKind, MessageStatus
from app.providers.llm.fake import FakeLLMClient, text_response, tool_response


def _setup(db_session, *, text="What colours does the Nexon come in?"):
    lead = Lead(
        name="Ravi",
        phone="+919876543210",
        interested_model="Nexon",
        status=LeadStatus.ENGAGED,
    )
    db_session.add(lead)
    db_session.flush()
    db_session.add(
        Message(
            lead_id=lead.id,
            direction=MessageDirection.INBOUND,
            kind=MessageKind.TEXT,
            body=text,
            status=MessageStatus.DELIVERED,
        )
    )
    db_session.commit()
    return lead


def _outbound_text(db_session):
    return db_session.scalars(
        select(Message).where(
            Message.direction == MessageDirection.OUTBOUND,
            Message.kind == MessageKind.TEXT,
        )
    ).all()


def test_plain_text_reply(db_session, mock_whatsapp):
    lead = _setup(db_session)
    llm = FakeLLMClient(
        default=text_response("The Nexon comes in several colours! Want a test drive? 🚗")
    )

    reply = respond_to_inbound(db_session, lead, whatsapp=mock_whatsapp, llm=llm)

    assert reply is not None and "Nexon" in reply
    db_session.refresh(lead)
    assert lead.status == LeadStatus.ENGAGED  # plain answer doesn't move the lead
    assert len(_outbound_text(db_session)) == 1
    assert len(mock_whatsapp.outbox) == 1


def test_request_test_drive_tool(db_session, mock_whatsapp):
    lead = _setup(db_session, text="Can I test drive it on Saturday?")
    llm = FakeLLMClient(
        responses=[
            tool_response("t1", "request_test_drive", {"preferred_time": "Saturday"}),
            text_response("Done! Our team will confirm your Saturday test drive. 🚗"),
        ]
    )

    reply = respond_to_inbound(db_session, lead, whatsapp=mock_whatsapp, llm=llm)

    db_session.refresh(lead)
    assert lead.status == LeadStatus.TEST_DRIVE_REQUESTED
    assert "confirm" in reply.lower()


def test_record_feedback_tool(db_session, mock_whatsapp):
    lead = _setup(db_session, text="The staff were super helpful, loved the visit!")
    llm = FakeLLMClient(
        responses=[
            tool_response(
                "f1",
                "record_feedback",
                {"feedback": "Staff were super helpful", "sentiment": "positive"},
            ),
            text_response("Thank you so much for the kind words! 🙏"),
        ]
    )

    respond_to_inbound(db_session, lead, whatsapp=mock_whatsapp, llm=llm)

    db_session.refresh(lead)
    assert lead.status == LeadStatus.FEEDBACK_GIVEN
    feedback = db_session.scalars(select(Feedback)).all()
    assert len(feedback) == 1
    assert feedback[0].sentiment == "positive"


def test_escalation_tool_sets_open_question(db_session, mock_whatsapp):
    lead = _setup(db_session, text="What's the on-road price?")
    llm = FakeLLMClient(
        responses=[
            tool_response(
                "e1",
                "escalate_to_sales",
                {"reason": "pricing", "question": "on-road price of the Nexon"},
            ),
            text_response("Our sales team will share the exact figures shortly!"),
        ]
    )

    respond_to_inbound(db_session, lead, whatsapp=mock_whatsapp, llm=llm)

    db_session.refresh(lead)
    assert lead.status == LeadStatus.HANDED_OFF
    assert lead.open_question and "price" in lead.open_question.lower()


def test_guardrail_blocks_price_and_escalates(db_session, mock_whatsapp):
    lead = _setup(db_session, text="how much?")
    # The model misbehaves and quotes a price; the guardrail must catch it.
    llm = FakeLLMClient(default=text_response("The Nexon starts at ₹8 lakh."))

    reply = respond_to_inbound(db_session, lead, whatsapp=mock_whatsapp, llm=llm)

    assert "₹" not in reply  # replaced with the safe fallback
    assert "sales team" in reply.lower()
    db_session.refresh(lead)
    assert lead.status == LeadStatus.HANDED_OFF


def test_opt_out_tool(db_session, mock_whatsapp):
    lead = _setup(db_session, text="stop messaging me")
    llm = FakeLLMClient(
        responses=[
            tool_response("o1", "opt_out", {}),
            text_response("No problem, you won't hear from us again."),
        ]
    )

    respond_to_inbound(db_session, lead, whatsapp=mock_whatsapp, llm=llm)

    db_session.refresh(lead)
    assert lead.opt_out is True
    assert lead.status == LeadStatus.OPTED_OUT
