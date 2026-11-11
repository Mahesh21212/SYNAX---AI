"""Health and capability endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from .. import db
from ..config import settings
from ..schemas import HealthOut

router = APIRouter(tags=["health"])

VERSION = "1.0.0"


@router.get("/health", response_model=HealthOut)
@router.get("/api/health", response_model=HealthOut, include_in_schema=False)
async def health() -> HealthOut:
    database_ok = await db.ping()
    return HealthOut(
        status="ok" if database_ok else "degraded",
        database=database_ok,
        openrouter=settings.openrouter_configured,
        version=VERSION,
    )
