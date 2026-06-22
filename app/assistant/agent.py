"""The inbound assistant: build context, run the tool loop, guard, send, persist."""
from __future__ import annotations

import datetime as dt

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.assistant.guardrail import guardrail_check, safe_fallback
from app.assistant.prompts import build_system_prompt
from app.assistant.tools import TOOL_SCHEMAS, execute_tool
from app.config import get_settings
from app.db.models import Event, Lead, Message
from app.domain.enums import (
    LeadStatus,
    MessageDirection,
    MessageKind,
    MessageStatus,
)
from app.providers.llm.base import LLMClient
from app.providers.whatsapp.base import WhatsAppProvider
from app.services.leads import try_set_status

_HISTORY_LIMIT = 10


def _build_messages(session: Session, lead: Lead) -> list[dict[str, object]]:
    rows = session.scalars(
        select(Message)
        .where(
            Message.lead_id == lead.id,
            Message.kind.in_([MessageKind.TEXT, MessageKind.TEMPLATE]),
        )
        .order_by(Message.created_at.desc())
        .limit(_HISTORY_LIMIT)
    ).all()
    rows = list(reversed(rows))

    messages: list[dict[str, object]] = []
    started = False
    for row in rows:
        role = "user" if row.direction == MessageDirection.INBOUND else "assistant"
        # The Anthropic API requires the first message to be a user turn.
        if not started and role != "user":
            continue
        started = True
        messages.append({"role": role, "content": row.body or ""})
    return messages


def _last_user_text(messages: list[dict[str, object]]) -> str | None:
    for message in reversed(messages):
        if message.get("role") == "user":
            return str(message.get("content"))
    return None


def run_agent(
    llm: LLMClient,
    *,
    system: str,
    messages: list[dict[str, object]],
    session: Session,
    lead: Lead,
    max_turns: int,
) -> str:
    convo = list(messages)
    settings = get_settings()
    final_text = ""

    for _ in range(max_turns):
        response = llm.create(
            system=system,
            messages=convo,
            tools=TOOL_SCHEMAS,
            max_tokens=settings.assistant_max_tokens,
        )
        text = " ".join(
            str(b.get("text", "")) for b in response.content if b.get("type") == "text"
        ).strip()
        tool_uses = [b for b in response.content if b.get("type") == "tool_use"]

        if not tool_uses:
            return text or final_text

        convo.append({"role": "assistant", "content": response.content})
        results: list[dict[str, object]] = []
        for tool_use in tool_uses:
            output = execute_tool(
                str(tool_use.get("name")),
                tool_use.get("input") or {},  # type: ignore[arg-type]
                session,
                lead,
            )
            results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": tool_use.get("id"),
                    "content": output,
                }
            )
        convo.append({"role": "user", "content": results})
        final_text = text or final_text

    return final_text or "Let me connect you with our team who can help further."


def _escalate(session: Session, lead: Lead, *, reason: str, question: str | None) -> None:
    if question:
        lead.open_question = question[:500]
    try_set_status(session, lead, LeadStatus.HANDED_OFF, reason=reason)
    session.add(Event(lead_id=lead.id, type="escalated", data={"reason": reason[:200]}))


def respond_to_inbound(
    session: Session,
    lead: Lead,
    *,
    whatsapp: WhatsAppProvider,
    llm: LLMClient,
) -> str | None:
    """Generate, guard, send, and persist a reply to the latest inbound message."""
    settings = get_settings()
    messages = _build_messages(session, lead)
    if not messages:
        return None

    system = build_system_prompt(lead)
    now = dt.datetime.now(dt.UTC)

    try:
        reply = run_agent(
            llm,
            system=system,
            messages=messages,
            session=session,
            lead=lead,
            max_turns=settings.assistant_max_turns,
        )
        ok, reason = guardrail_check(reply)
        if not ok:
            _escalate(
                session,
                lead,
                reason=f"guardrail:{reason}",
                question=_last_user_text(messages),
            )
            reply = safe_fallback(lead.preferred_language.value)
    except Exception as exc:  # noqa: BLE001 - any model/transport failure escalates safely
        _escalate(
            session, lead, reason=f"assistant_error:{exc}", question=_last_user_text(messages)
        )
        reply = safe_fallback(lead.preferred_language.value)

    result = whatsapp.send_text(lead.phone, reply)
    session.add(
        Message(
            lead_id=lead.id,
            direction=MessageDirection.OUTBOUND,
            kind=MessageKind.TEXT,
            body=reply,
            status=MessageStatus.SENT,
            provider_message_id=result.provider_message_id,
            sent_at=now,
        )
    )
    lead.last_contacted_at = now
    session.commit()
    return reply
