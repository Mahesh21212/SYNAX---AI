"""Persistent memory endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from .. import db as database
from ..deps import current_user, get_database
from ..schemas import MemoryCreate, MemoryOut
from ..services import memory as memory_service

router = APIRouter(prefix="/api/memory", tags=["memory"])


def _out(doc: dict) -> MemoryOut:
    return MemoryOut(
        id=str(doc["_id"]),
        content=doc["content"],
        kind=doc.get("kind", "fact"),
        conversation_id=doc.get("conversation_id"),
        created_at=doc["created_at"],
    )


@router.get("", response_model=list[MemoryOut])
async def list_memories(
    user_id: str = Depends(current_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
    limit: int = Query(default=100, ge=1, le=300),
) -> list[MemoryOut]:
    docs = await memory_service.list_all(db, user_id=user_id, limit=limit)
    return [_out(doc) for doc in docs]


@router.post("", response_model=MemoryOut, status_code=status.HTTP_201_CREATED)
async def create_memory(
    payload: MemoryCreate,
    user_id: str = Depends(current_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> MemoryOut:
    doc = await memory_service.create(
        db,
        user_id=user_id,
        content=payload.content,
        kind=payload.kind,
        conversation_id=payload.conversation_id,
    )
    return _out(doc)


@router.delete("/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_memory(
    memory_id: str,
    user_id: str = Depends(current_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> Response:
    deleted = await memory_service.delete(db, user_id=user_id, memory_id=memory_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Memory not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
