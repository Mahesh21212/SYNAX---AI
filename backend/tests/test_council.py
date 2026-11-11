"""Tests for the agent council's planning and parsing logic.

These run without a network connection: the provider is never called.
"""

from __future__ import annotations

from app.services.council import _default_plan, _parse_plan


def test_parse_plan_reads_plain_json():
    raw = '{"tasks": [{"agent": "researcher", "brief": "Find the facts"}], "reasoning": "x"}'
    plan = _parse_plan(raw)
    assert plan == [{"agent": "researcher", "brief": "Find the facts"}]


def test_parse_plan_strips_code_fences():
    raw = '```json\n{"tasks": [{"agent": "analyst", "brief": "Do the maths"}]}\n```'
    plan = _parse_plan(raw)
    assert plan == [{"agent": "analyst", "brief": "Do the maths"}]


def test_parse_plan_ignores_unknown_agents():
    raw = '{"tasks": [{"agent": "pirate", "brief": "Arr"}, {"agent": "writer", "brief": "Draft it"}]}'
    plan = _parse_plan(raw)
    assert plan == [{"agent": "writer", "brief": "Draft it"}]


def test_parse_plan_deduplicates_agents():
    raw = (
        '{"tasks": [{"agent": "writer", "brief": "First"}, '
        '{"agent": "writer", "brief": "Second"}]}'
    )
    plan = _parse_plan(raw)
    assert len(plan) == 1
    assert plan[0]["brief"] == "First"


def test_parse_plan_caps_at_three_tasks():
    raw = (
        '{"tasks": ['
        '{"agent": "researcher", "brief": "a"},'
        '{"agent": "analyst", "brief": "b"},'
        '{"agent": "writer", "brief": "c"},'
        '{"agent": "researcher", "brief": "d"}]}'
    )
    plan = _parse_plan(raw)
    assert len(plan) == 3


def test_parse_plan_handles_garbage():
    assert _parse_plan("I cannot help with that.") == []
    assert _parse_plan("") == []
    assert _parse_plan("{not json}") == []


def test_default_plan_is_usable():
    plan = _default_plan()
    assert len(plan) >= 1
    assert all(t["agent"] in {"researcher", "analyst", "writer"} for t in plan)
    assert all(t["brief"] for t in plan)
