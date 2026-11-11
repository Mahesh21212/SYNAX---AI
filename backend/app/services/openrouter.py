"""OpenRouter client: one place that talks to the model provider.

The API key lives only here, on the server. The browser never sees it.
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from typing import Any

import httpx

from ..config import settings

logger = logging.getLogger(__name__)


class OpenRouterError(RuntimeError):
    """Raised when the provider rejects a request or is unreachable."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code

    @property
    def model_unavailable(self) -> bool:
        """True when the failure is 'this model no longer exists'."""
        text = str(self).lower()
        return (
            self.status_code == 404
            or "no longer available" in text
            or (self.status_code == 400 and "not a valid model" in text)
        )

    @property
    def out_of_credits(self) -> bool:
        """True when the account cannot afford the request."""
        text = str(self).lower()
        return self.status_code == 402 or "requires more credits" in text


def _headers() -> dict[str, str]:
    if not settings.openrouter_configured:
        raise OpenRouterError(
            "OPENROUTER_API_KEY is not configured on the server. "
            "Add it to backend/.env and restart the API."
        )
    return {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": settings.openrouter_site_url,
        "X-Title": settings.openrouter_site_name,
    }


async def complete(
    *,
    model: str,
    messages: list[dict[str, Any]],
    temperature: float = 0.7,
    max_tokens: int = 2048,
    timeout: float = 120.0,
) -> dict[str, Any]:
    """Single non-streaming completion. Returns the raw provider payload."""
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            resp = await client.post(
                f"{settings.openrouter_base_url}/chat/completions",
                headers=_headers(),
                json=payload,
            )
        except httpx.HTTPError as exc:  # network-level failure
            raise OpenRouterError(f"Could not reach OpenRouter: {exc}") from exc

    if resp.status_code >= 400:
        detail = resp.text[:500]
        if resp.status_code == 402:
            raise OpenRouterError(
                "OpenRouter credits exhausted. The free models in the default "
                "config cost nothing, but this request used a paid model. "
                "Either switch the model in the picker to a ':free' one, or add "
                "credits at https://openrouter.ai/settings/credits",
                resp.status_code,
            )
        raise OpenRouterError(
            f"OpenRouter {resp.status_code}: {detail}", resp.status_code
        )

    return resp.json()


async def stream(
    *,
    model: str,
    messages: list[dict[str, Any]],
    temperature: float = 0.7,
    max_tokens: int = 2048,
    timeout: float = 180.0,
) -> AsyncIterator[str]:
    """Yield text deltas from a streaming completion."""
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": True,
    }

    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            async with client.stream(
                "POST",
                f"{settings.openrouter_base_url}/chat/completions",
                headers=_headers(),
                json=payload,
            ) as resp:
                if resp.status_code >= 400:
                    body = (await resp.aread()).decode("utf-8", "replace")[:500]
                    raise OpenRouterError(
                        f"OpenRouter {resp.status_code}: {body}", resp.status_code
                    )

                async for line in resp.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    data = line[6:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    choices = chunk.get("choices") or []
                    if not choices:
                        continue
                    delta = choices[0].get("delta") or {}
                    text = delta.get("content")
                    if text:
                        yield text
        except httpx.HTTPError as exc:  # network-level failure
            raise OpenRouterError(f"Could not reach OpenRouter: {exc}") from exc


def text_of(payload: dict[str, Any]) -> str:
    """Pull the assistant text out of a provider payload."""
    choices = payload.get("choices") or []
    if not choices:
        return ""
    message = choices[0].get("message") or {}
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = [
            part.get("text", "")
            for part in content
            if isinstance(part, dict) and part.get("type") == "text"
        ]
        return "".join(parts)
    return ""


def usage_of(payload: dict[str, Any]) -> dict[str, Any]:
    usage = payload.get("usage") or {}
    return {
        "prompt_tokens": usage.get("prompt_tokens", 0),
        "completion_tokens": usage.get("completion_tokens", 0),
        "total_tokens": usage.get("total_tokens", 0),
    }


async def list_models() -> list[dict[str, Any]]:
    """Fetch the public model catalogue (used by the model picker)."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(f"{settings.openrouter_base_url}/models")
    if resp.status_code >= 400:
        raise OpenRouterError(f"OpenRouter {resp.status_code}: {resp.text[:300]}")
    return resp.json().get("data", [])
