"""Browser WhatsApp simulator - chat with the assistant without real WhatsApp."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy.orm import Session

from app.assistant.agent import respond_to_inbound
from app.config import get_settings
from app.db.models import Lead
from app.db.session import get_db
from app.providers.llm.base import LLMClient
from app.providers.llm.factory import get_llm_client
from app.providers.whatsapp.base import WhatsAppProvider
from app.providers.whatsapp.factory import get_whatsapp_provider
from app.services import dashboard as dash
from app.services.inbound import handle_inbound
from app.templating import templates as _templates

router = APIRouter(prefix="/simulator", tags=["simulator"])


@router.get("", response_class=HTMLResponse)
def index(request: Request, db: Annotated[Session, Depends(get_db)]) -> Response:
    return _templates.TemplateResponse(
        request, "simulator_list.html", {"leads": dash.recent_leads(db, limit=50)}
    )


@router.get("/{lead_id}", response_class=HTMLResponse)
def chat(
    request: Request, lead_id: int, db: Annotated[Session, Depends(get_db)]
) -> Response:
    detail = dash.lead_detail(db, lead_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="lead not found")
    return _templates.TemplateResponse(request, "simulator.html", {"d": detail})


@router.post("/{lead_id}/send")
def send(
    lead_id: int,
    text: Annotated[str, Form()],
    db: Annotated[Session, Depends(get_db)],
    whatsapp: Annotated[WhatsAppProvider, Depends(get_whatsapp_provider)],
    llm: Annotated[LLMClient, Depends(get_llm_client)],
) -> RedirectResponse:
    lead = db.get(Lead, lead_id)
    if lead is None:
        raise HTTPException(status_code=404, detail="lead not found")
    if text.strip():
        # Simulate an inbound WhatsApp message from the customer, then let the
        # assistant respond exactly as it would for a real webhook delivery.
        handle_inbound(db, phone=lead.phone, text=text)
        if not lead.opt_out and get_settings().assistant_enabled:
            respond_to_inbound(db, lead, whatsapp=whatsapp, llm=llm)
    return RedirectResponse(f"/simulator/{lead_id}", status_code=303)
