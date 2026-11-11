"""End-to-end tests for the agent council with a mocked provider.

These prove the orchestration itself works — planning, parallel specialists,
critique, synthesis, and every degradation path — without needing a network
connection or an API key.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from app.services import council, openrouter


def _payload(text: str, prompt_tokens: int = 10, completion_tokens: int = 20) -> dict[str, Any]:
    return {
        "choices": [{"message": {"role": "assistant", "content": text}}],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
    }


class Recorder:
    """Stands in for openrouter.complete and records every call."""

    def __init__(self, responses: dict[str, str] | None = None, fail: set[str] | None = None):
        self.calls: list[dict[str, Any]] = []
        self.responses = responses or {}
        self.fail = fail or set()

    async def __call__(self, *, model: str, messages: list[dict[str, Any]], **kwargs):
        system = messages[0]["content"]
        agent = self._agent_of(system)
        self.calls.append({"agent": agent, "model": model, "messages": messages})

        if agent in self.fail:
            raise openrouter.OpenRouterError(f"{agent} unavailable")

        if agent in self.responses:
            return _payload(self.responses[agent])

        # Sensible defaults per agent.
        defaults = {
            "planner": '{"tasks": [{"agent": "researcher", "brief": "Find facts"}, '
            '{"agent": "analyst", "brief": "Do maths"}]}',
            "researcher": "RESEARCH NOTES: the facts.",
            "analyst": "ANALYSIS NOTES: the reasoning.",
            "writer": "DRAFT: the prose.",
            "critic": "FIX: tighten the opening.",
            "synth": "FINAL ANSWER: here it is.",
        }
        return _payload(defaults.get(agent, "ok"))

    @staticmethod
    def _agent_of(system: str) -> str:
        for agent in ("planner", "researcher", "analyst", "writer", "critic", "synth"):
            if f"You are the {agent.capitalize()}" in system or f"You are SYNAX" in system and agent == "synth":
                return agent
        return "synth"


@pytest.fixture
def recorder(monkeypatch):
    rec = Recorder()
    monkeypatch.setattr(openrouter, "complete", rec)
    return rec


async def run_council(rec: Recorder, **overrides):
    return await council.run(
        user_message=overrides.pop("user_message", "Explain X"),
        history=overrides.pop("history", []),
        **overrides,
    )


# --- Happy path -----------------------------------------------------------
@pytest.mark.asyncio
async def test_council_runs_full_pipeline(recorder):
    result = await run_council(recorder)

    agents = [call["agent"] for call in recorder.calls]
    assert agents[0] == "planner"
    assert "researcher" in agents
    assert "analyst" in agents
    assert "critic" in agents
    assert agents[-1] == "synth"

    assert result.content == "FINAL ANSWER: here it is."
    step_agents = [s.agent for s in result.steps]
    assert step_agents == ["planner", "researcher", "analyst", "critic", "synth"]
    assert all(s.status == "done" for s in result.steps)


@pytest.mark.asyncio
async def test_council_accumulates_usage(recorder):
    result = await run_council(recorder)
    # planner + 2 specialists + critic + synth = 5 calls, 30 tokens each
    assert result.usage["total_tokens"] == 5 * 30
    assert result.usage["prompt_tokens"] == 5 * 10


@pytest.mark.asyncio
async def test_specialists_run_concurrently(recorder):
    """Both specialists must be in flight before either returns."""
    order: list[str] = []

    async def slow_complete(*, model, messages, **kwargs):
        agent = Recorder._agent_of(messages[0]["content"])
        if agent in {"researcher", "analyst"}:
            order.append(f"start:{agent}")
            await asyncio.sleep(0.05)
            order.append(f"end:{agent}")
            return _payload(f"{agent} notes")
        return _payload(
            '{"tasks": [{"agent": "researcher", "brief": "a"}, '
            '{"agent": "analyst", "brief": "b"}]}'
            if agent == "planner"
            else "done"
        )

    openrouter.complete = slow_complete
    await run_council(Recorder())

    starts = [o for o in order if o.startswith("start:")]
    ends = [o for o in order if o.startswith("end:")]
    # Both start before either finishes => genuinely parallel.
    assert len(starts) == 2
    assert order[:2] == starts
    assert ends == order[2:]


@pytest.mark.asyncio
async def test_synth_receives_critique(recorder):
    await run_council(recorder)
    synth_call = [c for c in recorder.calls if c["agent"] == "synth"][-1]
    prompt = synth_call["messages"][-1]["content"]
    assert "FIX: tighten the opening." in prompt
    assert "RESEARCH NOTES" in prompt
    assert "ANALYSIS NOTES" in prompt


@pytest.mark.asyncio
async def test_synth_is_told_not_to_mention_the_council(recorder):
    await run_council(recorder)
    synth_call = [c for c in recorder.calls if c["agent"] == "synth"][-1]
    system = synth_call["messages"][0]["content"]
    assert "no mention of agents" in system.lower()


# --- Direct mode ----------------------------------------------------------
@pytest.mark.asyncio
async def test_direct_mode_skips_the_council(recorder):
    result = await run_council(recorder, use_agents=False)
    assert [c["agent"] for c in recorder.calls] == ["synth"]
    assert len(result.steps) == 1
    assert result.steps[0].agent == "synth"
    assert result.content == "FINAL ANSWER: here it is."


# --- Degradation paths ----------------------------------------------------
@pytest.mark.asyncio
async def test_planner_failure_falls_back_to_default_plan(monkeypatch):
    rec = Recorder(fail={"planner"})
    monkeypatch.setattr(openrouter, "complete", rec)

    result = await run_council(rec)

    planner_step = result.steps[0]
    assert planner_step.agent == "planner"
    assert planner_step.status == "error"
    # Default plan runs researcher + analyst, then critic + synth.
    agents = [c["agent"] for c in rec.calls]
    assert "researcher" in agents and "analyst" in agents
    assert result.content == "FINAL ANSWER: here it is."


@pytest.mark.asyncio
async def test_one_specialist_failure_does_not_kill_the_run(monkeypatch):
    rec = Recorder(fail={"researcher"})
    monkeypatch.setattr(openrouter, "complete", rec)

    result = await run_council(rec)

    statuses = {s.agent: s.status for s in result.steps}
    assert statuses["researcher"] == "error"
    assert statuses["analyst"] == "done"
    assert result.content == "FINAL ANSWER: here it is."


@pytest.mark.asyncio
async def test_critic_failure_still_produces_an_answer(monkeypatch):
    rec = Recorder(fail={"critic"})
    monkeypatch.setattr(openrouter, "complete", rec)

    result = await run_council(rec)

    statuses = {s.agent: s.status for s in result.steps}
    assert statuses["critic"] == "error"
    assert result.content == "FINAL ANSWER: here it is."


@pytest.mark.asyncio
async def test_all_specialists_failing_answers_directly(monkeypatch):
    rec = Recorder(fail={"researcher", "analyst", "writer"})
    monkeypatch.setattr(openrouter, "complete", rec)

    result = await run_council(rec)

    synth_steps = [s for s in result.steps if s.agent == "synth"]
    assert len(synth_steps) == 1
    assert "No specialist output" in (synth_steps[0].summary or "")
    assert result.content == "FINAL ANSWER: here it is."


@pytest.mark.asyncio
async def test_total_provider_outage_raises(monkeypatch):
    """If even the synthesizer fails, the caller gets a clear error."""
    rec = Recorder(fail={"planner", "researcher", "analyst", "writer", "critic", "synth"})
    monkeypatch.setattr(openrouter, "complete", rec)

    with pytest.raises(openrouter.OpenRouterError):
        await run_council(rec)


# --- Planner output handling ---------------------------------------------
@pytest.mark.asyncio
async def test_planner_can_request_a_writer(monkeypatch):
    rec = Recorder(
        responses={
            "planner": '{"tasks": [{"agent": "writer", "brief": "Draft the memo"}]}'
        }
    )
    monkeypatch.setattr(openrouter, "complete", rec)

    result = await run_council(rec)

    agents = [c["agent"] for c in rec.calls]
    assert "writer" in agents
    assert "researcher" not in agents
    assert result.content == "FINAL ANSWER: here it is."


@pytest.mark.asyncio
async def test_explicit_agent_selection_bypasses_planner(monkeypatch):
    rec = Recorder()
    monkeypatch.setattr(openrouter, "complete", rec)

    result = await run_council(rec, requested_agents=["analyst"])

    agents = [c["agent"] for c in rec.calls]
    assert "planner" not in agents
    assert "analyst" in agents
    assert result.content == "FINAL ANSWER: here it is."


# --- Context injection ----------------------------------------------------
@pytest.mark.asyncio
async def test_memory_and_documents_reach_the_specialists(monkeypatch):
    rec = Recorder()
    monkeypatch.setattr(openrouter, "complete", rec)

    await run_council(
        rec,
        memory_block="Known facts about this user:\n- (preference) Likes brevity",
        doc_block="### FILE: report.pdf\nRevenue was 4.2M",
    )

    specialist = [c for c in rec.calls if c["agent"] == "researcher"][0]
    system = specialist["messages"][0]["content"]
    assert "Likes brevity" in system
    assert "Revenue was 4.2M" in system


@pytest.mark.asyncio
async def test_history_is_passed_to_the_model(monkeypatch):
    rec = Recorder()
    monkeypatch.setattr(openrouter, "complete", rec)

    await run_council(
        rec,
        history=[
            {"role": "user", "content": "Earlier question"},
            {"role": "assistant", "content": "Earlier answer"},
        ],
    )

    specialist = [c for c in rec.calls if c["agent"] == "researcher"][0]
    contents = [m["content"] for m in specialist["messages"]]
    assert "Earlier question" in contents
    assert "Earlier answer" in contents
