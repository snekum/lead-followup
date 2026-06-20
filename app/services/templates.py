"""Load and render the approved cadence message templates (EN/HI/TE)."""
from __future__ import annotations

import functools
import json
from pathlib import Path
from typing import TYPE_CHECKING

from app.config import get_settings
from app.domain.enums import Language

if TYPE_CHECKING:
    from app.db.models import Lead

_TEMPLATES_PATH = (
    Path(__file__).resolve().parent.parent.parent / "seeds" / "templates.json"
)


@functools.lru_cache
def _templates() -> dict[str, dict[str, str]]:
    return json.loads(_TEMPLATES_PATH.read_text(encoding="utf-8"))


def get_body(step_key: str, language: Language) -> str:
    template = _templates()[step_key]
    # Fall back to English if a language variant is missing.
    return template.get(language.value) or template["en"]


def render_template(step_key: str, lead: Lead) -> str:
    body = get_body(step_key, lead.preferred_language)
    return body.format(
        name=lead.name,
        model=lead.interested_model or "Tata car",
        dealership=get_settings().dealership_name,
    )
