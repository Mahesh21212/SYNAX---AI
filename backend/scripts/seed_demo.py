"""Seed a conversation with a realistic answer for UI verification.

Writes directly to MongoDB so the transcript rendering (markdown, agent badge,
council trace) can be checked without calling a model.

Usage:
    python scripts/seed_demo.py
"""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from motor.motor_asyncio import AsyncIOMotorClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings  # noqa: E402

ANSWER = """## Short answer

They solve different problems. A single-prompt chatbot answers in one pass; a multi-agent system splits the work across specialists and reconciles the result.

## Where the difference actually shows up

| Dimension | Single prompt | Multi-agent |
|---|---|---|
| Passes over the problem | One | Several |
| Self-checking | None | A critic reviews drafts |
| Failure mode | Commits to its first framing | Can recover mid-run |
| Cost per answer | 1 call | 3–6 calls |
| Latency | Lower | Higher |

## The honest trade-off

Multi-agent is not strictly better. It wins when the task has separable parts — research plus analysis plus drafting — and loses when the question is simple, because you pay for orchestration you did not need.

```python
# The core of it: specialists run concurrently, not in sequence
results = await asyncio.gather(*(run_specialist(t) for t in plan))
```

The thing that makes it work is the **critic**: without a review step, you have just paid several times for the same blind spots.
"""

STEPS = [
    {"agent": "planner", "model": "anthropic/claude-3.5-sonnet", "status": "done",
     "summary": "Plan: researcher, analyst", "duration_ms": 1180},
    {"agent": "researcher", "model": "perplexity/llama-3.1-sonar-large-128k-online",
     "status": "done", "summary": "Establish the factual differences between the two architectures.",
     "duration_ms": 3410},
    {"agent": "analyst", "model": "anthropic/claude-3.5-sonnet", "status": "done",
     "summary": "Work through cost, latency and failure-mode trade-offs.", "duration_ms": 4025},
    {"agent": "critic", "model": "openai/gpt-4o-mini", "status": "done",
     "summary": "Reviewed the council's drafts", "duration_ms": 890},
    {"agent": "synth", "model": "anthropic/claude-3.5-sonnet", "status": "done",
     "summary": "Composed the final answer", "duration_ms": 2760},
]


async def main() -> None:
    client = AsyncIOMotorClient(settings.mongodb_uri)
    db = client[settings.mongodb_db]
    now = datetime.now(timezone.utc)

    conv = {
        "user_id": "local-user",
        "title": "Multi-agent vs single-prompt chatbots",
        "model": "anthropic/claude-3.5-sonnet",
        "pinned": True,
        "message_count": 2,
        "created_at": now - timedelta(minutes=4),
        "updated_at": now - timedelta(minutes=2),
    }
    conv_id = (await db.conversations.insert_one(conv)).inserted_id

    await db.messages.insert_many(
        [
            {
                "conversation_id": conv_id,
                "role": "user",
                "content": "Explain how a multi-agent system differs from a single-prompt chatbot.",
                "agent": None,
                "attachments": [],
                "citations": [],
                "created_at": now - timedelta(minutes=4),
            },
            {
                "conversation_id": conv_id,
                "role": "assistant",
                "content": ANSWER,
                "agent": "synth",
                "attachments": [],
                "citations": [],
                "created_at": now - timedelta(minutes=2),
            },
        ]
    )

    await db.runs.insert_one(
        {
            "conversation_id": conv_id,
            "user_id": "local-user",
            "model": "anthropic/claude-3.5-sonnet",
            "use_agents": True,
            "steps": STEPS,
            "usage": {"prompt_tokens": 4820, "completion_tokens": 1610, "total_tokens": 6430},
            "created_at": now - timedelta(minutes=2),
        }
    )

    print(f"seeded conversation {conv_id}")
    client.close()


if __name__ == "__main__":
    asyncio.run(main())
