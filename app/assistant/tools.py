"""The assistant's tool surface and their handlers.

Tools are the only way the assistant changes state. Handlers mutate the session
but do NOT commit - the caller (respond_to_inbound) commits once at the end.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models import Event, Feedback, Lead
from app.domain.enums import LeadStatus
from app.services.cadence import cancel_pending_touches
from app.services.leads import try_set_status

TOOL_SCHEMAS: list[dict[str, object]] = [
    {
        "name": "request_test_drive",
        "description": (
            "Record that the customer wants a test drive or a showroom revisit. "
            "The sales team confirms the actual slot."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "preferred_time": {
                    "type": "string",
                    "description": "Customer's preferred day/time, if mentioned.",
                },
                "model": {
                    "type": "string",
                    "description": "Tata model of interest, if mentioned.",
                },
            },
        },
    },
    {
        "name": "record_feedback",
        "description": "Record the customer's feedback about their showroom visit or experience.",
        "input_schema": {
            "type": "object",
            "properties": {
                "feedback": {
                    "type": "string",
                    "description": "The customer's feedback, in their words.",
                },
                "sentiment": {
                    "type": "string",
                    "enum": ["positive", "neutral", "negative"],
                },
            },
            "required": ["feedback"],
        },
    },
    {
        "name": "escalate_to_sales",
        "description": (
            "Hand the conversation to a human salesperson. Use for any question about price, "
            "discount, finance/EMI, exchange value, stock availability, or delivery dates - or "
            "anything you cannot answer from the approved FAQ."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "reason": {"type": "string", "description": "Why this needs a human."},
                "question": {
                    "type": "string",
                    "description": "The customer's exact question to pass along.",
                },
            },
            "required": ["reason"],
        },
    },
    {
        "name": "opt_out",
        "description": "The customer wants to stop receiving messages or is not interested.",
        "input_schema": {"type": "object", "properties": {}},
    },
]


def execute_tool(
    name: str, tool_input: dict[str, object], session: Session, lead: Lead
) -> str:
    tool_input = tool_input or {}

    if name == "request_test_drive":
        try_set_status(
            session, lead, LeadStatus.TEST_DRIVE_REQUESTED, reason="assistant:test_drive"
        )
        session.add(
            Event(
                lead_id=lead.id,
                type="test_drive_requested",
                data={k: str(v) for k, v in tool_input.items()},
            )
        )
        return "Recorded the test-drive request; the sales team will confirm the timing."

    if name == "record_feedback":
        text = str(tool_input.get("feedback", "")).strip()
        sentiment = tool_input.get("sentiment")
        session.add(
            Feedback(
                lead_id=lead.id,
                text=text,
                sentiment=str(sentiment) if sentiment else None,
            )
        )
        try_set_status(
            session, lead, LeadStatus.FEEDBACK_GIVEN, reason="assistant:feedback"
        )
        return "Thanks, the feedback has been recorded."

    if name == "escalate_to_sales":
        question = tool_input.get("question")
        if question:
            lead.open_question = str(question)[:500]
        reason = str(tool_input.get("reason", "assistant"))
        try_set_status(session, lead, LeadStatus.HANDED_OFF, reason=reason)
        session.add(Event(lead_id=lead.id, type="escalated", data={"reason": reason[:200]}))
        return "Connected to the sales team; they'll follow up shortly."

    if name == "opt_out":
        lead.opt_out = True
        try_set_status(session, lead, LeadStatus.OPTED_OUT, reason="assistant:opt_out")
        cancel_pending_touches(session, lead)
        session.add(Event(lead_id=lead.id, type="opt_out"))
        return "The customer has been opted out."

    return f"Unknown tool: {name}"
