"""Shared pytest fixtures.

Tests run against an in-memory Mongo (mongomock-motor), so the suite needs no
database server and no network access.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ.setdefault("MONGODB_URI", "mongodb://localhost:27017")
os.environ.setdefault("OPENROUTER_API_KEY", "")


@pytest.fixture(autouse=True)
def in_memory_db(monkeypatch):
    """Replace the Mongo client with an in-memory one for every test."""
    from mongomock_motor import AsyncMongoMockClient

    from app import db as database

    client = AsyncMongoMockClient()
    monkeypatch.setattr(database, "_client", client, raising=False)
    yield client
    monkeypatch.setattr(database, "_client", None, raising=False)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"
