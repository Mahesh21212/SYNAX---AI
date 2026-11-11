"""The /api/chat endpoint end to end, with the provider mocked.

Proves the persistence path: user turn stored, assistant turn stored, step
trace recorded, conversation counters updated, history fed back in.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app import db as database
from app.main import app
from app.services import openrouter

client = TestClient(app)


def _payload(text: str) -> dict[str, Any]:
    return {
        "choices": [{"message": {"role": "assistant", "content": text}}],
        "usage": {"prompt_tokens": 5, "completion_tokens": 7, "total_tokens": 12},
    }


@pytest.fixture
def mocked_provider(monkeypatch):
    calls: list[dict[str, Any]] = []

    async def fake_complete(*, model, messages, **kwargs):
        system = messages[0]["content"]
        calls.append({"model": model, "system": system, "messages": messages})
        if "You are the Planner" in system:
            return _payload('{"tasks": [{"agent": "analyst", "brief": "Work it out"}]}')
        if "You are the Critic" in system:
            return _payload("FIX: be specific.")
        if "You are SYNAX" in system:
            return _payload("The final answer.")
        return _payload("Analyst notes.")

    monkeypatch.setattr(openrouter, "complete", fake_complete)
    return calls


def test_chat_creates_conversation_and_persists_both_turns(mocked_provider):
    res = client.post("/api/chat", json={"message": "What is 2+2?"})
    assert res.status_code == 200, res.text

    body = res.json()
    conv_id = body["conversation_id"]
    assert body["message"]["role"] == "assistant"
    assert body["message"]["content"] == "The final answer."
    assert len(body["steps"]) >= 3

    history = client.get(f"/api/conversations/{conv_id}/messages").json()
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[0]["content"] == "What is 2+2?"
    assert history[1]["role"] == "assistant"

    conversation = client.get(f"/api/conversations/{conv_id}").json()
    assert conversation["message_count"] == 2
    assert conversation["title"] == "What is 2+2?"


def test_chat_appends_to_existing_conversation(mocked_provider):
    first = client.post("/api/chat", json={"message": "First question"}).json()
    conv_id = first["conversation_id"]

    second = client.post(
        "/api/chat",
        json={"message": "Second question", "conversation_id": conv_id},
    )
    assert second.status_code == 200

    history = client.get(f"/api/conversations/{conv_id}/messages").json()
    assert len(history) == 4
    assert [m["role"] for m in history] == ["user", "assistant", "user", "assistant"]

    conversation = client.get(f"/api/conversations/{conv_id}").json()
    assert conversation["message_count"] == 4


def test_chat_passes_prior_turns_as_history(mocked_provider):
    first = client.post("/api/chat", json={"message": "My name is Ada."}).json()
    conv_id = first["conversation_id"]

    mocked_provider.clear()
    client.post(
        "/api/chat",
        json={"message": "What is my name?", "conversation_id": conv_id},
    )

    # Every call in the second turn should carry the earlier exchange.
    specialist = [c for c in mocked_provider if "You are the Analyst" in c["system"]]
    assert specialist, "analyst was not called"
    contents = [m["content"] for m in specialist[0]["messages"]]
    assert "My name is Ada." in contents
    assert "The final answer." in contents


def test_chat_records_a_run_document(mocked_provider):
    body = client.post("/api/chat", json={"message": "Trace me"}).json()
    conv_id = body["conversation_id"]

    import asyncio

    async def fetch():
        db = database.get_db()
        return await db.runs.find_one({"conversation_id": __import__("bson").ObjectId(conv_id)})

    run = asyncio.get_event_loop().run_until_complete(fetch())
    assert run is not None
    assert run["usage"]["total_tokens"] > 0
    assert len(run["steps"]) == len(body["steps"])


def test_chat_direct_mode_returns_single_step(mocked_provider):
    res = client.post(
        "/api/chat", json={"message": "Quick one", "use_agents": False}
    )
    assert res.status_code == 200
    body = res.json()
    assert len(body["steps"]) == 1
    assert body["steps"][0]["agent"] == "synth"


def test_chat_with_document_attachment_injects_text(mocked_provider, tmp_path):
    from app.services import documents as doc_service

    sample = tmp_path / "report.txt"
    sample.write_text("Quarterly revenue was 4.2 million.", encoding="utf-8")

    with sample.open("rb") as handle:
        upload = client.post(
            "/api/documents",
            files={"file": ("report.txt", handle, "text/plain")},
        )
    assert upload.status_code == 201
    doc_id = upload.json()["id"]

    mocked_provider.clear()
    res = client.post(
        "/api/chat",
        json={"message": "Summarise the file", "attachment_ids": [doc_id]},
    )
    assert res.status_code == 200

    specialist = [c for c in mocked_provider if "You are the Analyst" in c["system"]]
    assert specialist
    assert "Quarterly revenue was 4.2 million." in specialist[0]["system"]


def test_chat_returns_503_when_provider_fails(monkeypatch):
    async def boom(*args, **kwargs):
        raise openrouter.OpenRouterError("OPENROUTER_API_KEY is not configured")

    monkeypatch.setattr(openrouter, "complete", boom)

    res = client.post("/api/chat", json={"message": "Will fail"})
    assert res.status_code == 503
    assert "OPENROUTER_API_KEY" in res.json()["detail"]


def test_chat_does_not_persist_assistant_turn_on_failure(monkeypatch):
    async def boom(*args, **kwargs):
        raise openrouter.OpenRouterError("provider down")

    monkeypatch.setattr(openrouter, "complete", boom)

    res = client.post("/api/chat", json={"message": "Will fail"})
    assert res.status_code == 503

    # The conversation was created, but only the user turn exists.
    conversations = client.get("/api/conversations").json()
    target = next(c for c in conversations if c["title"].startswith("Will fail"))
    history = client.get(f"/api/conversations/{target['id']}/messages").json()
    assert [m["role"] for m in history] == ["user"]
