"""Model catalogue for the picker, proxied so the key stays server-side."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from ..config import settings
from ..deps import current_user
from ..services import openrouter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/models", tags=["models"])

# Curated fallback so the picker still works before a key is configured.
FALLBACK_MODELS: list[dict[str, Any]] = [
    {"id": "anthropic/claude-3.5-sonnet", "name": "Claude 3.5 Sonnet", "context_length": 200000},
    {"id": "anthropic/claude-3.5-haiku", "name": "Claude 3.5 Haiku", "context_length": 200000},
    {"id": "openai/gpt-4o", "name": "GPT-4o", "context_length": 128000},
    {"id": "openai/gpt-4o-mini", "name": "GPT-4o mini", "context_length": 128000},
    {"id": "google/gemini-2.0-flash-001", "name": "Gemini 2.0 Flash", "context_length": 1000000},
    {"id": "meta-llama/llama-3.3-70b-instruct", "name": "Llama 3.3 70B", "context_length": 131072},
    {"id": "mistralai/mistral-large", "name": "Mistral Large", "context_length": 128000},
    {"id": "deepseek/deepseek-chat", "name": "DeepSeek Chat", "context_length": 64000},
]


@router.get("")
async def list_models(
    user_id: str = Depends(current_user),
    limit: int = Query(default=60, ge=1, le=400),
) -> dict[str, Any]:
    if not settings.openrouter_configured:
        return {
            "source": "fallback",
            "configured": False,
            "models": FALLBACK_MODELS,
        }

    try:
        raw = await openrouter.list_models()
    except openrouter.OpenRouterError as exc:
        logger.warning("Model catalogue unavailable: %s", exc)
        return {"source": "fallback", "configured": True, "models": FALLBACK_MODELS}

    models = [
        {
            "id": m.get("id"),
            "name": m.get("name") or m.get("id"),
            "context_length": m.get("context_length"),
            "description": (m.get("description") or "")[:240],
        }
        for m in raw
        if m.get("id")
    ]
    models.sort(key=lambda m: m["name"] or "")
    return {"source": "openrouter", "configured": True, "models": models[:limit]}
