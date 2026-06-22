"""System prompt construction for the inbound assistant."""
from __future__ import annotations

import functools
from pathlib import Path
from typing import TYPE_CHECKING

from app.config import get_settings

if TYPE_CHECKING:
    from app.db.models import Lead

_FAQ_PATH = Path(__file__).resolve().parent.parent.parent / "seeds" / "faq.md"
_LANGUAGE = {"en": "English", "hi": "Hindi", "te": "Telugu"}


@functools.lru_cache
def _faq() -> str:
    return _FAQ_PATH.read_text(encoding="utf-8")


def build_system_prompt(lead: Lead) -> str:
    settings = get_settings()
    language = _LANGUAGE.get(lead.preferred_language.value, "English")
    model_clause = (
        f" and looked at the Tata {lead.interested_model}"
        if lead.interested_model
        else ""
    )
    open_question = (
        f"\n- There is an earlier unresolved question from this lead to address: "
        f"{lead.open_question}"
        if lead.open_question
        else ""
    )
    return f"""You are the friendly WhatsApp assistant for {settings.dealership_name}, \
a Tata car dealership.

You are messaging {lead.name}, who recently visited the showroom{model_clause}. Reply in \
{language}, kept short and natural for WhatsApp (1-3 sentences; an occasional emoji is fine).

Rules:
- Only state facts found in the APPROVED FAQ below. If you are unsure, say you'll check with \
the team rather than guessing.
- NEVER quote prices, discounts, EMI / finance figures, exchange values, stock availability, or \
delivery dates. For ANY such question, call the escalate_to_sales tool instead of answering.
- To book a test drive or a revisit, call request_test_drive.
- To capture the customer's feedback about their showroom visit, call record_feedback.
- If the customer asks to stop messages or says they are not interested, call opt_out.
- Never invent offers, specifications, or commitments.{open_question}

APPROVED FAQ:
{_faq()}
"""
