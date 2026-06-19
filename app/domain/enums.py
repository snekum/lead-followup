"""Domain enumerations. Stored as their string values (portable across DBs)."""
from __future__ import annotations

from enum import StrEnum


class LocationType(StrEnum):
    SHOWROOM = "showroom"
    WORKSHOP = "workshop"


class StaffRole(StrEnum):
    SALES_EXEC = "sales_exec"
    MANAGER = "manager"
    ADMIN = "admin"


class LeadSource(StrEnum):
    WALK_IN = "walk_in"
    CSV_IMPORT = "csv_import"
    FORM = "form"


class Language(StrEnum):
    EN = "en"
    HI = "hi"
    TE = "te"


class LeadStatus(StrEnum):
    NEW = "new"
    CONTACTED = "contacted"
    ENGAGED = "engaged"
    TEST_DRIVE_REQUESTED = "test_drive_requested"
    FEEDBACK_GIVEN = "feedback_given"
    HANDED_OFF = "handed_off"
    WON = "won"
    LOST = "lost"
    OPTED_OUT = "opted_out"
    UNREACHABLE = "unreachable"
