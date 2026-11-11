"""Test candidate free models with a real prompt and generous token budget."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services import openrouter  # noqa: E402

CANDIDATES = [
    "baidu/ernie-5.5-flash-preview:free",
    "recursive/flint-v1.0:free",
    "nvidia/nemotron-3.5-lightning:free",
    "dots-studio/dots-3-note-preview:free",
]

PROMPT = (
    "In two sentences, explain the difference between a multi-agent system "
    "and a single-prompt chatbot."
)


async def probe(model: str) -> None:
    try:
        payload = await openrouter.complete(
            model=model,
            messages=[{"role": "user", "content": PROMPT}],
            max_tokens=600,
            temperature=0.3,
            timeout=120.0,
        )
        text = openrouter.text_of(payload).strip()
        usage = openrouter.usage_of(payload)
        print(f"\n--- {model}")
        print(f"    usage: {usage}")
        print(f"    len={len(text)}")
        print(f"    text: {text[:300]!r}")
    except Exception as exc:  # noqa: BLE001
        print(f"\n--- {model}\n    FAIL: {str(exc)[:140]}")


async def main() -> None:
    for model in CANDIDATES:
        await probe(model)


if __name__ == "__main__":
    asyncio.run(main())
