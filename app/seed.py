"""Seed reference data (locations, staff) and optionally the sample leads.

Run after migrations:  python -m app.seed
Idempotent: skips if locations already exist.
"""
from __future__ import annotations

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Location, StaffMember
from app.db.session import SessionLocal
from app.domain.enums import LocationType, StaffRole
from app.services.intake import import_file

SEEDS_DIR = Path(__file__).resolve().parent.parent / "seeds"

_LOCATIONS = [
    ("Tata Motors - Banjara Hills", LocationType.SHOWROOM),
    ("Tata Motors - Kukatpally", LocationType.SHOWROOM),
    ("Tata Motors - Gachibowli", LocationType.SHOWROOM),
    ("Tata Service - Uppal", LocationType.WORKSHOP),
    ("Tata Service - Miyapur", LocationType.WORKSHOP),
]

_STAFF = [
    ("Rahul Verma", StaffRole.SALES_EXEC),
    ("Deepa Menon", StaffRole.SALES_EXEC),
    ("Suresh Kumar", StaffRole.MANAGER),
]


def seed_locations_and_staff(session: Session) -> None:
    if session.scalar(select(Location).limit(1)):
        print("Locations already seeded; skipping.")
        return
    locations = [Location(name=name, type=ltype) for name, ltype in _LOCATIONS]
    session.add_all(locations)
    session.flush()
    showroom_id = locations[0].id
    for name, role in _STAFF:
        session.add(StaffMember(name=name, role=role, location_id=showroom_id))
    session.commit()
    print(f"Seeded {len(locations)} locations and {len(_STAFF)} staff members.")


def seed_sample_leads(session: Session) -> None:
    csv_path = SEEDS_DIR / "sample_leads.csv"
    result = import_file(session, csv_path.name, csv_path.read_bytes())
    print(f"Sample leads import: {result.as_dict()}")


def run() -> None:
    with SessionLocal() as session:
        seed_locations_and_staff(session)
        seed_sample_leads(session)


if __name__ == "__main__":
    run()
