from sqlalchemy import func, select

from app.db.models import Lead
from app.domain.enums import Language
from app.services.intake import import_leads


def test_import_dedupes_and_validates(db_session) -> None:
    rows = [
        {"name": "Ravi", "phone": "9876543210", "model": "Nexon", "language": "telugu"},
        {"name": "Imran", "phone": "098765 43210"},  # duplicate of Ravi
        {"name": "Bad", "phone": "12345"},  # invalid phone
        {"name": "Anjali", "phone": "+91 99887 76655"},  # valid, distinct
        {"name": "", "phone": "9000000000"},  # missing name
    ]

    result = import_leads(db_session, rows)

    assert result.imported == 2
    assert result.duplicates == 1
    assert result.invalid == 2
    assert db_session.scalar(select(func.count()).select_from(Lead)) == 2

    ravi = db_session.scalar(select(Lead).where(Lead.name == "Ravi"))
    assert ravi is not None
    assert ravi.phone == "+919876543210"
    assert ravi.preferred_language == Language.TE
    assert ravi.interested_model == "Nexon"


def test_import_empty(db_session) -> None:
    result = import_leads(db_session, [])
    assert result.imported == 0
