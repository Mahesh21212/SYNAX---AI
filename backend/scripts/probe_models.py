"""Probe which candidate models actually respond on this key."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services import openrouter  # noqa: E402

CANDIDATES = [
    "anthropic/claude-opus-4.5",
    "anthropic/claude-haiku-4.5",
    "anthropic/claude-fable-5.2",
    "openai/gpt-5.1",
    "openai/gpt-5-mini",
    "google/gemini-2.5-flash",
    "google/gemini-2.5-pro",
    "perplexity/sonar-pro",
    "deepseek/deepseek-v4",
    "meta-llama/llama-3.3-70b-instruct",
]


async def probe(model: str) -> tuple[str, str]:
    try:
        payload = await openrouter.complete(
            model=model,
            messages=[{"role": "user", "content": "Reply with exactly: OK"}],
            max_tokens=16,
            temperature=0,
            timeout=45.0,
        )
        text = openrouter.text_of(payload).strip()
        return model, f"OK -> {text[:40]!r}"
    except Exception as exc:  # noqa: BLE001
        return model, f"FAIL -> {str(exc)[:110]}"


async def main() -> None:
    results = await asyncio.gather(*(probe(m) for m in CANDIDATES))
    for model, status in results:
        print(f"{model:45} {status}")


if __name__ == "__main__":
    asyncio.run(main())
