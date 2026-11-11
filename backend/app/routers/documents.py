"""Document upload, listing and deletion."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from motor.motor_asyncio import AsyncIOMotorDatabase

from .. import db as database
from ..config import settings
from ..deps import current_user, get_database
from ..schemas import DocumentOut
from ..services import documents as doc_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/documents", tags=["documents"])


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _out(doc: dict) -> DocumentOut:
    return DocumentOut(
        id=str(doc["_id"]),
        filename=doc["filename"],
        content_type=doc.get("content_type", "application/octet-stream"),
        size_bytes=int(doc.get("size_bytes", 0)),
        pages=doc.get("pages"),
        char_count=int(doc.get("char_count", 0)),
        excerpt=doc.get("excerpt"),
        created_at=doc["created_at"],
    )


@router.post("", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    user_id: str = Depends(current_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> DocumentOut:

    filename = Path(file.filename or "upload").name
    suffix = Path(filename).suffix.lower()
    if suffix not in doc_service.SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                f"Unsupported file type '{suffix or 'unknown'}'. Supported: "
                + ", ".join(sorted(doc_service.SUPPORTED_EXTENSIONS))
            ),
        )

    raw = await file.read()
    if len(raw) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds the {settings.max_upload_mb} MB limit",
        )
    if not raw:
        raise HTTPException(status_code=400, detail="Empty file")

    stored_name = f"{uuid.uuid4().hex}{suffix}"
    stored_path = settings.upload_path / stored_name
    stored_path.write_bytes(raw)

    try:
        extracted = doc_service.extract(stored_path, file.content_type)
    except doc_service.UnsupportedDocument as exc:
        stored_path.unlink(missing_ok=True)
        raise HTTPException(status_code=415, detail=str(exc)) from exc
    except Exception as exc:  # malformed file
        stored_path.unlink(missing_ok=True)
        logger.warning("Extraction failed for %s: %s", filename, exc)
        raise HTTPException(
            status_code=422, detail=f"Could not read '{filename}': {exc}"
        ) from exc

    doc = {
        "user_id": user_id,
        "filename": filename,
        "stored_name": stored_name,
        "content_type": file.content_type or "application/octet-stream",
        "size_bytes": len(raw),
        "pages": extracted.pages,
        "char_count": len(extracted.text),
        "truncated": extracted.truncated,
        "text": extracted.text,
        "excerpt": doc_service.excerpt(extracted.text),
        "created_at": _now(),
    }
    result = await db.documents.insert_one(doc)
    doc["_id"] = result.inserted_id
    return _out(doc)


@router.get("", response_model=list[DocumentOut])
async def list_documents(
    user_id: str = Depends(current_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
    limit: int = Query(default=100, ge=1, le=300),
) -> list[DocumentOut]:
    cursor = (
        db.documents.find({"user_id": user_id}, {"text": 0})
        .sort("created_at", -1)
        .limit(limit)
    )
    return [_out(doc) for doc in await cursor.to_list(length=limit)]


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: str,
    user_id: str = Depends(current_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> Response:
    try:
        oid = ObjectId(document_id)
    except (InvalidId, TypeError) as exc:
        raise HTTPException(status_code=400, detail="Invalid id") from exc

    doc = await db.documents.find_one_and_delete({"_id": oid, "user_id": user_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    stored = settings.upload_path / doc.get("stored_name", "")
    if stored.exists():
        stored.unlink(missing_ok=True)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
