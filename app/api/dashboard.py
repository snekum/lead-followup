"""Server-rendered manager dashboard + handoff actions."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy.orm import Session

from app.db.models import Event, Lead
from app.db.session import get_db
from app.domain.enums import LeadStatus
from app.domain.lead_state import InvalidTransition
from app.services import dashboard as dash
from app.services.leads import change_status
from app.templating import templates as _templates

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("", response_class=HTMLResponse)
def overview(request: Request, db: Annotated[Session, Depends(get_db)]) -> Response:
    return _templates.TemplateResponse(
        request,
        "overview.html",
        {
            "metrics": dash.metrics(db),
            "funnel": dash.funnel(db),
            "needs_human": dash.needs_human(db),
            "recent": dash.recent_leads(db),
        },
    )


@router.get("/handoff", response_class=HTMLResponse)
def handoff(request: Request, db: Annotated[Session, Depends(get_db)]) -> Response:
    return _templates.TemplateResponse(
        request, "handoff.html", {"leads": dash.needs_human(db)}
    )


@router.get("/leads/{lead_id}", response_class=HTMLResponse)
def lead_detail(
    request: Request, lead_id: int, db: Annotated[Session, Depends(get_db)]
) -> Response:
    detail = dash.lead_detail(db, lead_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="lead not found")
    return _templates.TemplateResponse(request, "lead_detail.html", {"d": detail})


@router.post("/leads/{lead_id}/status")
def set_status_action(
    lead_id: int,
    to: Annotated[str, Form()],
    db: Annotated[Session, Depends(get_db)],
) -> RedirectResponse:
    lead = db.get(Lead, lead_id)
    if lead is None:
        raise HTTPException(status_code=404, detail="lead not found")
    try:
        change_status(db, lead, LeadStatus(to), reason="manager")
    except (InvalidTransition, ValueError):
        pass  # ignore invalid manual transitions
    return RedirectResponse(f"/dashboard/leads/{lead_id}", status_code=303)


@router.post("/leads/{lead_id}/resolve")
def resolve_action(
    lead_id: int, db: Annotated[Session, Depends(get_db)]
) -> RedirectResponse:
    lead = db.get(Lead, lead_id)
    if lead is not None:
        lead.open_question = None
        db.add(Event(lead_id=lead.id, type="question_resolved"))
        db.commit()
    return RedirectResponse(f"/dashboard/leads/{lead_id}", status_code=303)
