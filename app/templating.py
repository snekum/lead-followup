"""Shared Jinja2 templates instance for the dashboard and simulator."""
from __future__ import annotations

from pathlib import Path

from fastapi.templating import Jinja2Templates

from app.config import get_settings

templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parent.parent / "templates")
)
templates.env.globals["dealership"] = get_settings().dealership_name
