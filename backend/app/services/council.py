"""SYNAX AI multi-agent council.

The council is a small, explicit pipeline rather than a black box:

    planner  -> decides which specialists are needed and what each should do
    researcher / analyst / writer -> run in parallel on their own briefs
    critic   -> reviews the drafts and names the weakest points
    synth    -> writes the single answer the user sees

Every step is recorded so the UI can show what actually happened, and every
specialist gets only the context it needs. If the planner fails or the model
provider is unavailable, the council degrades to a single direct answer.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any

from ..config import settings
from ..schemas import AgentName, AgentStep
from . import openrouter

logger = logging.getLogger(__name__)

SPECIALISTS: tuple[AgentName, ...] = ("researcher", "analyst", "writer")

AGENT_MODEL: dict[str, str] = {
    "planner": settings.synax_planner_model,
    "researcher": settings.synax_researcher_model,
    "analyst": settings.synax_analyst_model,
    "writer": settings.synax_writer_model,
    "critic": settings.synax_critic_model,
    "synth": settings.synax_default_model,
}

AGENT_BRIEF: dict[str, str] = {
    "planner": (
        "You are the Planner in a multi-agent council. Break the user's request "
        "into the smallest set of specialist tasks that would actually improve "
        "the answer. Respond with JSON only, no prose, in this exact shape:\n"
        '{"tasks": [{"agent": "researcher|analyst|writer", "brief": "one sentence"}], '
        '"reasoning": "one sentence"}\n'
        "Use 1-3 tasks. Choose researcher for external facts or current context, "
        "analyst for numbers, comparisons, structured reasoning or code, writer "
        "for drafting prose or restructuring content. Never invent a task that "
        "does not help."
    ),
    "researcher": (
        "You are the Researcher. Gather and state the concrete facts, figures, "
        "definitions and context needed for the request. Be specific. Flag "
        "anything you are not certain of as UNVERIFIED rather than guessing. "
        "Do not write the final answer; produce research notes."
    ),
    "analyst": (
        "You are the Analyst. Work the numbers and the structure: comparisons, "
        "trade-offs, edge cases, calculations, code correctness, risks. Show the "
        "reasoning steps that matter. Do not write the final answer; produce "
        "analysis notes with explicit conclusions."
    ),
    "writer": (
        "You are the Writer. Produce a clear, well-organised draft that answers "
        "the request directly. Lead with the answer, keep it tight, use structure "
        "only where it helps. This is a draft for the council to review."
    ),
    "critic": (
        "You are the Critic. Review the drafts against the user's request. Name "
        "the specific weaknesses: unsupported claims, missing angles, wrong tone, "
        "arithmetic or logic errors, filler. Be blunt and concrete. Do not rewrite "
        "the answer; produce a short list of required fixes, most important first."
    ),
    "synth": (
        "You are SYNAX, the lead agent. You have the council's work in front of "
        "you. Write the single final answer the user sees: direct, accurate, "
        "well-structured, no mention of agents, drafts, critics or internal "
        "process. Lead with the answer. Never state a figure that is not in the "
        "provided material; if something is unknown, say so plainly."
    ),
}


@dataclass
class CouncilResult:
    content: str
    steps: list[AgentStep] = field(default_factory=list)
    usage: dict[str, int] = field(default_factory=dict)
    citations: list[dict[str, Any]] = field(default_factory=list)


def _system(agent: AgentName, memory_block: str, doc_block: str) -> str:
    parts = [AGENT_BRIEF[agent]]
    if memory_block:
        parts.append(memory_block)
    if doc_block:
        parts.append(doc_block)
    return "\n\n".join(parts)


def _history_block(history: list[dict[str, Any]], limit: int = 10) -> list[dict[str, str]]:
    """Convert stored messages into provider chat turns."""
    turns: list[dict[str, str]] = []
    for msg in history[-limit:]:
        role = msg.get("role")
        content = (msg.get("content") or "").strip()
        if role in {"user", "assistant"} and content:
            turns.append({"role": role, "content": content})
    return turns


def _accumulate(usage: dict[str, int], payload: dict[str, Any]) -> None:
    for key, value in openrouter.usage_of(payload).items():
        usage[key] = usage.get(key, 0) + int(value or 0)


async def _call(
    agent: AgentName,
    *,
    user_message: str,
    history: list[dict[str, Any]],
    memory_block: str,
    doc_block: str,
    model: str | None = None,
    temperature: float = 0.6,
    max_tokens: int = 1600,
) -> tuple[str, dict[str, Any]]:
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": _system(agent, memory_block, doc_block)}
    ]
    messages.extend(_history_block(history))
    messages.append({"role": "user", "content": user_message})

    payload = await openrouter.complete(
        model=model or AGENT_MODEL[agent],
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return openrouter.text_of(payload).strip(), payload


def _parse_plan(raw: str) -> list[dict[str, str]]:
    """Parse the planner's JSON, tolerating fences and stray prose."""
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("```")[1] if "```" in text[3:] else text
        text = text.lstrip("json").strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        return []
    try:
        data = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return []

    tasks: list[dict[str, str]] = []
    for task in data.get("tasks", []):
        if not isinstance(task, dict):
            continue
        agent = str(task.get("agent", "")).lower().strip()
        brief = str(task.get("brief", "")).strip()
        if agent in SPECIALISTS and brief:
            tasks.append({"agent": agent, "brief": brief})
    # de-duplicate agents, keep first brief
    seen: set[str] = set()
    unique: list[dict[str, str]] = []
    for task in tasks:
        if task["agent"] in seen:
            continue
        seen.add(task["agent"])
        unique.append(task)
    return unique[:3]


def _default_plan() -> list[dict[str, str]]:
    return [
        {"agent": "researcher", "brief": "Establish the facts and context needed to answer accurately."},
        {"agent": "analyst", "brief": "Work through the reasoning, numbers and trade-offs."},
    ]


async def run(
    *,
    user_message: str,
    history: list[dict[str, Any]],
    memory_block: str = "",
    doc_block: str = "",
    model: str | None = None,
    use_agents: bool = True,
    requested_agents: list[AgentName] | None = None,
) -> CouncilResult:
    """Run the council and return the final answer plus a step trace."""
    steps: list[AgentStep] = []
    usage: dict[str, int] = {}

    # --- Direct mode -----------------------------------------------------
    if not use_agents:
        started = time.perf_counter()
        text, payload = await _call(
            "synth",
            user_message=user_message,
            history=history,
            memory_block=memory_block,
            doc_block=doc_block,
            model=model,
            max_tokens=2400,
        )
        _accumulate(usage, payload)
        steps.append(
            AgentStep(
                agent="synth",
                model=model or AGENT_MODEL["synth"],
                status="done",
                summary="Direct answer",
                duration_ms=int((time.perf_counter() - started) * 1000),
            )
        )
        return CouncilResult(content=text, steps=steps, usage=usage)

    # --- Plan ------------------------------------------------------------
    plan: list[dict[str, str]] = []
    if requested_agents:
        plan = [
            {"agent": a, "brief": f"Contribute your specialist view on: {user_message[:200]}"}
            for a in requested_agents
            if a in SPECIALISTS
        ]
    else:
        started = time.perf_counter()
        try:
            raw, payload = await _call(
                "planner",
                user_message=user_message,
                history=history,
                memory_block=memory_block,
                doc_block="",
                temperature=0.2,
                max_tokens=400,
            )
            _accumulate(usage, payload)
            plan = _parse_plan(raw)
            steps.append(
                AgentStep(
                    agent="planner",
                    model=AGENT_MODEL["planner"],
                    status="done",
                    summary=(
                        "Plan: " + ", ".join(t["agent"] for t in plan)
                        if plan
                        else "Planner returned no tasks; using default plan"
                    ),
                    duration_ms=int((time.perf_counter() - started) * 1000),
                )
            )
        except openrouter.OpenRouterError as exc:
            logger.warning("Planner failed: %s", exc)
            steps.append(
                AgentStep(
                    agent="planner",
                    model=AGENT_MODEL["planner"],
                    status="error",
                    summary=str(exc)[:200],
                    duration_ms=int((time.perf_counter() - started) * 1000),
                )
            )

    if not plan:
        plan = _default_plan()

    # --- Specialists in parallel ----------------------------------------
    async def run_specialist(task: dict[str, str]) -> tuple[AgentStep, str]:
        agent = task["agent"]  # type: ignore[assignment]
        brief = task["brief"]
        started = time.perf_counter()
        prompt = (
            f"User request:\n{user_message}\n\n"
            f"Your assignment from the planner:\n{brief}\n\n"
            "Return your notes only."
        )
        try:
            text, payload = await _call(
                agent,  # type: ignore[arg-type]
                user_message=prompt,
                history=history,
                memory_block=memory_block,
                doc_block=doc_block,
                temperature=0.5,
                max_tokens=1400,
            )
            _accumulate(usage, payload)
            return (
                AgentStep(
                    agent=agent,  # type: ignore[arg-type]
                    model=AGENT_MODEL[agent],
                    status="done",
                    summary=brief,
                    duration_ms=int((time.perf_counter() - started) * 1000),
                ),
                text,
            )
        except openrouter.OpenRouterError as exc:
            logger.warning("%s failed: %s", agent, exc)
            return (
                AgentStep(
                    agent=agent,  # type: ignore[arg-type]
                    model=AGENT_MODEL[agent],
                    status="error",
                    summary=str(exc)[:200],
                    duration_ms=int((time.perf_counter() - started) * 1000),
                ),
                "",
            )

    results = await asyncio.gather(*(run_specialist(t) for t in plan))
    drafts: dict[str, str] = {}
    for step, text in results:
        steps.append(step)
        if text:
            drafts[step.agent] = text

    if not drafts:
        # Nothing came back from the specialists: answer directly.
        started = time.perf_counter()
        text, payload = await _call(
            "synth",
            user_message=user_message,
            history=history,
            memory_block=memory_block,
            doc_block=doc_block,
            model=model,
            max_tokens=2400,
        )
        _accumulate(usage, payload)
        steps.append(
            AgentStep(
                agent="synth",
                model=model or AGENT_MODEL["synth"],
                status="done",
                summary="No specialist output; answered directly",
                duration_ms=int((time.perf_counter() - started) * 1000),
            )
        )
        return CouncilResult(content=text, steps=steps, usage=usage)

    council_block = "\n\n".join(
        f"### {agent.upper()} NOTES\n{text}" for agent, text in drafts.items()
    )

    # --- Critique --------------------------------------------------------
    critique = ""
    started = time.perf_counter()
    try:
        critique, payload = await _call(
            "critic",
            user_message=(
                f"User request:\n{user_message}\n\nCouncil notes:\n{council_block}\n\n"
                "List the fixes required before this can be sent."
            ),
            history=[],
            memory_block=memory_block,
            doc_block="",
            temperature=0.2,
            max_tokens=700,
        )
        _accumulate(usage, payload)
        steps.append(
            AgentStep(
                agent="critic",
                model=AGENT_MODEL["critic"],
                status="done",
                summary="Reviewed the council's drafts",
                duration_ms=int((time.perf_counter() - started) * 1000),
            )
        )
    except openrouter.OpenRouterError as exc:
        steps.append(
            AgentStep(
                agent="critic",
                model=AGENT_MODEL["critic"],
                status="error",
                summary=str(exc)[:200],
                duration_ms=int((time.perf_counter() - started) * 1000),
            )
        )

    # --- Synthesise ------------------------------------------------------
    started = time.perf_counter()
    synth_prompt = (
        f"User request:\n{user_message}\n\n"
        f"Council notes:\n{council_block}\n\n"
        + (f"Critic's required fixes:\n{critique}\n\n" if critique else "")
        + "Write the final answer now. Address the critic's fixes. "
        "Do not mention the council, the notes or the critique."
    )
    text, payload = await _call(
        "synth",
        user_message=synth_prompt,
        history=history,
        memory_block=memory_block,
        doc_block=doc_block,
        model=model,
        temperature=0.6,
        max_tokens=2600,
    )
    _accumulate(usage, payload)
    steps.append(
        AgentStep(
            agent="synth",
            model=model or AGENT_MODEL["synth"],
            status="done",
            summary="Composed the final answer",
            duration_ms=int((time.perf_counter() - started) * 1000),
        )
    )

    return CouncilResult(content=text, steps=steps, usage=usage)
