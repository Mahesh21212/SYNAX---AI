"""MongoDB connection lifecycle and index management."""

from __future__ import annotations

import logging

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING

from .config import settings

logger = logging.getLogger(__name__)

_client: AsyncIOMotorClient | None = None


async def connect() -> None:
    """Open the Mongo client and ensure indexes exist."""
    global _client
    if _client is not None:
        return

    _client = AsyncIOMotorClient(
        settings.mongodb_uri,
        serverSelectionTimeoutMS=5000,
        tz_aware=True,
    )
    await _client.admin.command("ping")
    await _ensure_indexes(get_db())
    logger.info("MongoDB connected: %s/%s", settings.mongodb_uri, settings.mongodb_db)


async def disconnect() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None


def get_db() -> AsyncIOMotorDatabase:
    if _client is None:
        raise RuntimeError("Database not initialised. Call connect() first.")
    return _client[settings.mongodb_db]


async def ping() -> bool:
    """Return True when the database answers a ping."""
    try:
        if _client is None:
            return False
        await _client.admin.command("ping")
        return True
    except Exception:  # pragma: no cover - defensive
        return False


async def _ensure_indexes(db: AsyncIOMotorDatabase) -> None:
    await db.conversations.create_index(
        [("user_id", ASCENDING), ("updated_at", DESCENDING)]
    )
    await db.conversations.create_index([("user_id", ASCENDING), ("pinned", DESCENDING)])
    await db.messages.create_index(
        [("conversation_id", ASCENDING), ("created_at", ASCENDING)]
    )
    await db.memories.create_index(
        [("user_id", ASCENDING), ("created_at", DESCENDING)]
    )
    await db.documents.create_index(
        [("user_id", ASCENDING), ("created_at", DESCENDING)]
    )
    await db.documents.create_index([("conversation_id", ASCENDING)])
    await db.runs.create_index(
        [("conversation_id", ASCENDING), ("created_at", DESCENDING)]
    )
