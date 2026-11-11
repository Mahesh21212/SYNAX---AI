"""Persistent memory: durable facts the assistant carries across conversations."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

MAX_MEMORIES_IN_PROMPT = 12
STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "have", "about",
    "what", "when", "where", "which", "your", "you", "are", "was", "were",
    "will", "would", "could", "should", "there", "their", "them", "then",
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _tokens(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]{3,}", text.lower())
    return {w for w in words if w not in STOPWORDS}


def score_memory(memory: dict[str, Any], query_tokens: set[str]) -> float:
    """Cheap lexical relevance score, used to pick which memories to inject."""
    if not query_tokens:
        return 0.0
    mem_tokens = _tokens(memory.get("content", ""))
    if not mem_tokens:
        return 0.0
    overlap = len(mem_tokens & query_tokens)
    return overlap / (len(mem_tokens) ** 0.5)


async def create(
    db: AsyncIOMotorDatabase,
    *,
    user_id: str,
    content: str,
    kind: str = "fact",
    conversation_id: str | None = None,
) -> dict[str, Any]:
    doc = {
        "user_id": user_id,
        "content": content.strip(),
        "kind": kind,
        "conversation_id": conversation_id,
        "created_at": _now(),
    }
    result = await db.memories.insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc


async def list_all(
    db: AsyncIOMotorDatabase, *, user_id: str, limit: int = 100
) -> list[dict[str, Any]]:
    cursor = (
        db.memories.find({"user_id": user_id})
        .sort("created_at", -1)
        .limit(limit)
    )
    return await cursor.to_list(length=limit)


async def delete(
    db: AsyncIOMotorDatabase, *, user_id: str, memory_id: str
) -> bool:
    if not ObjectId.is_valid(memory_id):
        return False
    result = await db.memories.delete_one(
        {"_id": ObjectId(memory_id), "user_id": user_id}
    )
    return result.deleted_count > 0


async def relevant(
    db: AsyncIOMotorDatabase,
    *,
    user_id: str,
    query: str,
    limit: int = MAX_MEMORIES_IN_PROMPT,
) -> list[dict[str, Any]]:
    """Return the memories most relevant to the current question."""
    memories = await list_all(db, user_id=user_id, limit=200)
    if not memories:
        return []

    query_tokens = _tokens(query)
    ranked = sorted(
        memories,
        key=lambda m: (score_memory(m, query_tokens), m["created_at"]),
        reverse=True,
    )
    selected = [m for m in ranked if score_memory(m, query_tokens) > 0][:limit]
    if not selected:
        selected = memories[: min(3, len(memories))]
    return selected


def render(memories: list[dict[str, Any]]) -> str:
    """Format memories for inclusion in a system prompt."""
    if not memories:
        return ""
    lines = [f"- ({m.get('kind', 'fact')}) {m['content']}" for m in memories]
    return "Known facts about this user:\n" + "\n".join(lines)
