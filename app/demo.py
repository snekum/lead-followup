"""End-to-end demo on the mock WhatsApp provider + a scripted assistant.

Runs the full arc offline (no credentials): walk-in -> Day-0 template -> customer
reply -> grounded answer -> test-drive booking -> price question -> human handoff.

Run after migrations:  python -m app.demo   (or `make demo`)
"""
from __future__ import annotations

import contextlib
import datetime as dt
import sys
import time

from app.assistant.agent import respond_to_inbound
from app.db.session import SessionLocal
from app.domain.enums import Language, LeadSource
from app.providers.llm.fake import FakeLLMClient, text_response, tool_response
from app.providers.whatsapp.mock import MockWhatsAppProvider
from app.services.cadence import process_due_touches
from app.services.inbound import handle_inbound
from app.services.leads import create_lead


def _rule(title: str) -> None:
    print(f"\n=== {title} ===")


def run() -> None:
    # Emoji in replies break the default Windows console (cp1252); force UTF-8.
    with contextlib.suppress(Exception):
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]

    mock = MockWhatsAppProvider()
    phone = "+9198" + f"{int(time.time()) % 100000000:08d}"  # unique-ish, valid IN mobile

    with SessionLocal() as session:
        _rule("1. Walk-in lead captured")
        lead = create_lead(
            session,
            name="Demo Customer",
            phone=phone,
            interested_model="Nexon",
            preferred_language=Language.EN,
            source=LeadSource.WALK_IN,
        )
        print(f"Lead #{lead.id} {lead.name} ({lead.phone}) - status {lead.status.value}")
        print("Cadence scheduled (Day 0/2/5/9).")

        _rule("2. Day-0 follow-up sent (cadence engine, mock WhatsApp)")
        # A non-quiet time just past Day 0 so exactly the first nudge is due.
        now = (dt.datetime.now(dt.UTC) + dt.timedelta(days=1)).replace(hour=6, minute=30)
        print("process_due_touches ->", process_due_touches(session, mock, now=now))
        if mock.outbox:
            print("OUT (template):", mock.outbox[-1]["template"])
        session.refresh(lead)
        print("status:", lead.status.value)

        _rule("3. Customer replies")
        handle_inbound(session, phone=phone, text="Yes! I really liked the Nexon.")
        reply = respond_to_inbound(
            session,
            lead,
            whatsapp=mock,
            llm=FakeLLMClient(
                default=text_response(
                    "So glad to hear that! Would you like to book a test drive? 🚗"
                )
            ),
        )
        session.refresh(lead)
        print("CUSTOMER : Yes! I really liked the Nexon.")
        print("ASSISTANT:", reply)
        print("status:", lead.status.value)

        _rule("4. Customer books a test drive (tool: request_test_drive)")
        handle_inbound(session, phone=phone, text="Can I test drive it this Saturday?")
        reply = respond_to_inbound(
            session,
            lead,
            whatsapp=mock,
            llm=FakeLLMClient(
                responses=[
                    tool_response("t1", "request_test_drive", {"preferred_time": "Saturday"}),
                    text_response("Done! Our team will confirm your Saturday test drive. 🚗"),
                ]
            ),
        )
        session.refresh(lead)
        print("CUSTOMER : Can I test drive it this Saturday?")
        print("ASSISTANT:", reply)
        print("status:", lead.status.value)

        _rule("5. Price question -> escalated to a human (tool: escalate_to_sales)")
        handle_inbound(session, phone=phone, text="Great. What's the on-road price and EMI?")
        reply = respond_to_inbound(
            session,
            lead,
            whatsapp=mock,
            llm=FakeLLMClient(
                responses=[
                    tool_response(
                        "e1",
                        "escalate_to_sales",
                        {"reason": "pricing", "question": "on-road price and EMI for the Nexon"},
                    ),
                    text_response(
                        "Our sales team will share the exact pricing and EMI options shortly!"
                    ),
                ]
            ),
        )
        session.refresh(lead)
        print("CUSTOMER : What's the on-road price and EMI?")
        print("ASSISTANT:", reply)
        print("status:", lead.status.value, "| open_question:", lead.open_question)

        _rule("Done")
        print(f"Dashboard:  http://localhost:8000/dashboard/leads/{lead.id}")
        print(f"Simulator:  http://localhost:8000/simulator/{lead.id}")


if __name__ == "__main__":
    run()
