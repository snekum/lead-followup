"""Pydantic request/response schemas for the API."""
from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, ConfigDict

from app.domain.enums import Language, LeadSource, LeadStatus


class LeadCreate(BaseModel):
    name: str
    phone: str
    interested_model: str | None = None
    budget: str | None = None
    visit_date: dt.date | None = None
    preferred_language: Language = Language.EN
    location_id: int | None = None
    notes: str | None = None
    source: LeadSource = LeadSource.FORM


class LeadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    phone: str
    interested_model: str | None
    budget: str | None
    visit_date: dt.date | None
    preferred_language: Language
    status: LeadStatus
    source: LeadSource
    created_at: dt.datetime
