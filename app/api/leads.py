"""Lead intake API: manual create, list, and bulk CSV/Excel import."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.domain.enums import LeadStatus
from app.schemas import LeadCreate, LeadOut
from app.services.intake import import_file
from app.services.leads import DuplicateLead, create_lead, list_leads
from app.services.phone import PhoneError

router = APIRouter(prefix="/leads", tags=["leads"])


@router.post("", response_model=LeadOut, status_code=201)
def create_lead_endpoint(
    payload: LeadCreate, db: Annotated[Session, Depends(get_db)]
) -> LeadOut:
    try:
        lead = create_lead(
            db,
            name=payload.name,
            phone=payload.phone,
            source=payload.source,
            interested_model=payload.interested_model,
            budget=payload.budget,
            visit_date=payload.visit_date,
            preferred_language=payload.preferred_language,
            location_id=payload.location_id,
            notes=payload.notes,
        )
    except PhoneError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except DuplicateLead as exc:
        raise HTTPException(status_code=409, detail=f"lead already exists: {exc}") from exc
    return LeadOut.model_validate(lead)


@router.get("", response_model=list[LeadOut])
def list_leads_endpoint(
    db: Annotated[Session, Depends(get_db)],
    status: LeadStatus | None = None,
    limit: int = 100,
) -> list[LeadOut]:
    leads = list_leads(db, status=status, limit=limit)
    return [LeadOut.model_validate(lead) for lead in leads]


@router.post("/import")
async def import_leads_endpoint(
    db: Annotated[Session, Depends(get_db)],
    file: Annotated[UploadFile, File(...)],
) -> dict[str, object]:
    content = await file.read()
    result = import_file(db, file.filename or "upload.csv", content)
    return result.as_dict()
