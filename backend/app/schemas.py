"""Pydantic schemas shared across routers and services."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

Role = Literal["user", "assistant", "system", "tool"]
AgentName = Literal["planner", "researcher", "analyst", "writer", "critic", "synth"]


# ---------------------------------------------------------------------------
# Conversations
# ---------------------------------------------------------------------------
class ConversationCreate(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    model: str | None = None


class ConversationUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    pinned: bool | None = None
    model: str | None = None


class Conversation(BaseModel):
    id: str
    title: str
    model: str
    pinned: bool = False
    message_count: int = 0
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------
class Attachment(BaseModel):
    id: str
    filename: str
    content_type: str
    size_bytes: int
    excerpt: str | None = None


class Message(BaseModel):
    id: str
    conversation_id: str
    role: Role
    content: str
    agent: AgentName | None = None
    attachments: list[Attachment] = Field(default_factory=list)
    citations: list[dict[str, Any]] = Field(default_factory=list)
    created_at: datetime


class ChatRequest(BaseModel):
    conversation_id: str | None = None
    message: str = Field(min_length=1, max_length=32000)
    model: str | None = None
    attachment_ids: list[str] = Field(default_factory=list)
    use_agents: bool = True
    agents: list[AgentName] | None = None


class AgentStep(BaseModel):
    agent: AgentName
    model: str
    status: Literal["pending", "running", "done", "error"] = "pending"
    summary: str | None = None
    duration_ms: int | None = None


class ChatResponse(BaseModel):
    conversation_id: str
    message: Message
    steps: list[AgentStep] = Field(default_factory=list)
    usage: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------
class DocumentOut(BaseModel):
    id: str
    filename: str
    content_type: str
    size_bytes: int
    pages: int | None = None
    char_count: int = 0
    excerpt: str | None = None
    created_at: datetime


# ---------------------------------------------------------------------------
# Memory
# ---------------------------------------------------------------------------
class MemoryCreate(BaseModel):
    content: str = Field(min_length=1, max_length=2000)
    kind: Literal["fact", "preference", "context"] = "fact"
    conversation_id: str | None = None


class MemoryOut(BaseModel):
    id: str
    content: str
    kind: str
    conversation_id: str | None = None
    created_at: datetime


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------
class HealthOut(BaseModel):
    status: Literal["ok", "degraded"]
    database: bool
    openrouter: bool
    version: str
