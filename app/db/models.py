"""SQLAlchemy ORM models.

Enums are stored as VARCHAR + CHECK (``native_enum=False``) so migrations stay
simple and the schema is portable (Postgres in prod, SQLite in tests).
"""
from __future__ import annotations

import datetime as dt

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.domain.enums import (
    Language,
    LeadSource,
    LeadStatus,
    LocationType,
    StaffRole,
)


def _enum(enum_cls: type) -> sa.Enum:
    return sa.Enum(
        enum_cls,
        native_enum=False,
        length=40,
        values_callable=lambda e: [m.value for m in e],
    )


def _now() -> sa.ColumnElement[dt.datetime]:
    return sa.func.now()


class Location(Base):
    __tablename__ = "locations"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(sa.String(120))
    type: Mapped[LocationType] = mapped_column(_enum(LocationType))
    city: Mapped[str] = mapped_column(sa.String(80), default="Hyderabad")
    timezone: Mapped[str] = mapped_column(sa.String(40), default="Asia/Kolkata")
    created_at: Mapped[dt.datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=_now()
    )

    staff: Mapped[list[StaffMember]] = relationship(back_populates="location")
    leads: Mapped[list[Lead]] = relationship(back_populates="location")


class StaffMember(Base):
    __tablename__ = "staff_members"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(sa.String(120))
    phone: Mapped[str | None] = mapped_column(sa.String(20))
    role: Mapped[StaffRole] = mapped_column(_enum(StaffRole), default=StaffRole.SALES_EXEC)
    location_id: Mapped[int | None] = mapped_column(sa.ForeignKey("locations.id"))
    active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[dt.datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=_now()
    )

    location: Mapped[Location | None] = relationship(back_populates="staff")


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(sa.String(120))
    # E.164, e.g. +919876543210. Unique => one lead per phone (dedupe).
    phone: Mapped[str] = mapped_column(sa.String(20))
    source: Mapped[LeadSource] = mapped_column(
        _enum(LeadSource), default=LeadSource.CSV_IMPORT
    )
    interested_model: Mapped[str | None] = mapped_column(sa.String(80))
    budget: Mapped[str | None] = mapped_column(sa.String(60))
    visit_date: Mapped[dt.date | None] = mapped_column(sa.Date)
    preferred_language: Mapped[Language] = mapped_column(
        _enum(Language), default=Language.EN
    )
    status: Mapped[LeadStatus] = mapped_column(
        _enum(LeadStatus), default=LeadStatus.NEW, index=True
    )
    location_id: Mapped[int | None] = mapped_column(sa.ForeignKey("locations.id"))
    assigned_to_id: Mapped[int | None] = mapped_column(
        sa.ForeignKey("staff_members.id")
    )
    consent: Mapped[bool] = mapped_column(default=True)
    opt_out: Mapped[bool] = mapped_column(default=False)
    # An unanswered question carried into the next follow-up (set on escalation).
    open_question: Mapped[str | None] = mapped_column(sa.Text)
    notes: Mapped[str | None] = mapped_column(sa.Text)
    last_contacted_at: Mapped[dt.datetime | None] = mapped_column(
        sa.DateTime(timezone=True)
    )
    created_at: Mapped[dt.datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=_now()
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=_now(), onupdate=_now()
    )

    location: Mapped[Location | None] = relationship(back_populates="leads")
    assigned_to: Mapped[StaffMember | None] = relationship()
    events: Mapped[list[Event]] = relationship(
        back_populates="lead", cascade="all, delete-orphan"
    )

    __table_args__ = (sa.UniqueConstraint("phone", name="uq_leads_phone"),)


class Event(Base):
    """Append-only audit/lifecycle log for a lead."""

    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True)
    lead_id: Mapped[int] = mapped_column(sa.ForeignKey("leads.id"))
    type: Mapped[str] = mapped_column(sa.String(60))
    data: Mapped[dict[str, object] | None] = mapped_column(sa.JSON)
    created_at: Mapped[dt.datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=_now()
    )

    lead: Mapped[Lead] = relationship(back_populates="events")
