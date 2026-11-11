"""Shared dependencies: identity, database handle, optional bearer auth."""

from __future__ import annotations

import hmac

from fastapi import Header, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from . import db as database
from .config import settings

DEFAULT_USER = "local-user"


async def get_database() -> AsyncIOMotorDatabase:
    """Provide the Mongo handle, or a clear 503 when it is not connected."""
    try:
        return database.get_db()
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Database unavailable. Check MONGODB_URI in backend/.env and "
                "that MongoDB is running."
            ),
        ) from exc


async def current_user(
    authorization: str | None = Header(default=None),
    x_synax_user: str | None = Header(default=None),
) -> str:
    """Resolve the caller.

    When SYNAX_API_TOKEN is set, a matching bearer token is required. Otherwise
    the API is open for local development and the caller may identify itself
    with X-Synax-User (defaults to a single local user).
    """
    if settings.synax_api_token:
        expected = f"Bearer {settings.synax_api_token}"
        if not authorization or not hmac.compare_digest(authorization, expected):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing bearer token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return x_synax_user or DEFAULT_USER

    return x_synax_user or DEFAULT_USER
