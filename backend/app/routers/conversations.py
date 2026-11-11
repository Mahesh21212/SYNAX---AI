"""Conversation CRUD and message history."""

from __future__ import annotations

from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from .. import db as database
from ..config import settings
from ..deps import current_user, get_database
from ..schemas import (
    Conversation,
    ConversationCreate,
    ConversationUpdate,
    Message,
)

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _oid(value: str) -> ObjectId:
    try:
        return ObjectId(value)
    except (InvalidId, TypeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid id"
        ) from exc


def _conversation_out(doc: dict) -> Conversation:
    return Conversation(
        id=str(doc["_id"]),
        title=doc.get("title") or "New chat",
        model=doc.get("model") or settings.synax_default_model,
        pinned=bool(doc.get("pinned", False)),
        message_count=int(doc.get("message_count", 0)),
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


def _message_out(doc: dict) -> Message:
    return Message(
        id=str(doc["_id"]),
        conversation_id=str(doc["conversation_id"]),
        role=doc["role"],
        content=doc.get("content", ""),
        agent=doc.get("agent"),
        attachments=doc.get("attachments", []),
        citations=doc.get("citations", []),
        created_at=doc["created_at"],
    )


@router.get("", response_model=list[Conversation])
async def list_conversations(
    user_id: str = Depends(current_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
    limit: int = Query(default=100, ge=1, le=300),
) -> list[Conversation]:
    cursor = (
        db.conversations.find({"user_id": user_id})
        .sort([("pinned", -1), ("updated_at", -1)])
        .limit(limit)
    )
    return [_conversation_out(doc) for doc in await cursor.to_list(length=limit)]


@router.post("", response_model=Conversation, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    payload: ConversationCreate,
    user_id: str = Depends(current_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> Conversation:
    now = _now()
    doc = {
        "user_id": user_id,
        "title": (payload.title or "New chat").strip()[:200],
        "model": payload.model or settings.synax_default_model,
        "pinned": False,
        "message_count": 0,
        "created_at": now,
        "updated_at": now,
    }
    result = await db.conversations.insert_one(doc)
    doc["_id"] = result.inserted_id
    return _conversation_out(doc)


@router.get("/{conversation_id}", response_model=Conversation)
async def get_conversation(
    conversation_id: str,
    user_id: str = Depends(current_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> Conversation:
    doc = await db.conversations.find_one(
        {"_id": _oid(conversation_id), "user_id": user_id}
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return _conversation_out(doc)


@router.patch("/{conversation_id}", response_model=Conversation)
async def update_conversation(
    conversation_id: str,
    payload: ConversationUpdate,
    user_id: str = Depends(current_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> Conversation:
    updates: dict = {}
    if payload.title is not None:
        updates["title"] = payload.title.strip()[:200] or "New chat"
    if payload.pinned is not None:
        updates["pinned"] = payload.pinned
    if payload.model is not None:
        updates["model"] = payload.model
    if not updates:
        raise HTTPException(status_code=400, detail="Nothing to update")

    updates["updated_at"] = _now()
    doc = await db.conversations.find_one_and_update(
        {"_id": _oid(conversation_id), "user_id": user_id},
        {"$set": updates},
        return_document=True,
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return _conversation_out(doc)


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: str,
    user_id: str = Depends(current_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> Response:
    oid = _oid(conversation_id)
    result = await db.conversations.delete_one({"_id": oid, "user_id": user_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Conversation not found")
    await db.messages.delete_many({"conversation_id": oid})
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{conversation_id}/messages", response_model=list[Message])
async def list_messages(
    conversation_id: str,
    user_id: str = Depends(current_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
    limit: int = Query(default=500, ge=1, le=1000),
) -> list[Message]:
    oid = _oid(conversation_id)
    owned = await db.conversations.find_one({"_id": oid, "user_id": user_id})
    if not owned:
        raise HTTPException(status_code=404, detail="Conversation not found")

    cursor = (
        db.messages.find({"conversation_id": oid})
        .sort("created_at", 1)
        .limit(limit)
    )
    return [_message_out(doc) for doc in await cursor.to_list(length=limit)]


@router.delete("/{conversation_id}/messages", status_code=status.HTTP_204_NO_CONTENT)
async def clear_messages(
    conversation_id: str,
    user_id: str = Depends(current_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> Response:
    oid = _oid(conversation_id)
    owned = await db.conversations.find_one({"_id": oid, "user_id": user_id})
    if not owned:
        raise HTTPException(status_code=404, detail="Conversation not found")
    await db.messages.delete_many({"conversation_id": oid})
    await db.conversations.update_one(
        {"_id": oid}, {"$set": {"message_count": 0, "updated_at": _now()}}
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
