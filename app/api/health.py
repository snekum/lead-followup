"""Liveness / readiness endpoints."""
from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/")
def root() -> dict[str, str]:
    return {"service": "saarthi", "status": "ok"}


@router.get("/health")
def health() -> dict[str, str]:
    """Liveness check. Intentionally does not touch the DB so it stays cheap."""
    return {"status": "ok"}
