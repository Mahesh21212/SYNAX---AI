"""Tests for document extraction and memory ranking."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.services import documents as doc_service
from app.services import memory as memory_service


# --- Documents ------------------------------------------------------------
def test_extract_plain_text(tmp_path: Path):
    path = tmp_path / "notes.txt"
    path.write_text("Hello SYNAX.\nSecond line.", encoding="utf-8")
    result = doc_service.extract(path)
    assert "Hello SYNAX." in result.text
    assert result.truncated is False


def test_extract_markdown(tmp_path: Path):
    path = tmp_path / "readme.md"
    path.write_text("# Title\n\nBody text.", encoding="utf-8")
    result = doc_service.extract(path)
    assert "# Title" in result.text


def test_extract_csv(tmp_path: Path):
    path = tmp_path / "data.csv"
    path.write_text("a,b\n1,2\n3,4\n", encoding="utf-8")
    result = doc_service.extract(path)
    assert "a | b" in result.text
    assert "1 | 2" in result.text


def test_extract_json_pretty_prints(tmp_path: Path):
    path = tmp_path / "payload.json"
    path.write_text(json.dumps({"key": "value"}), encoding="utf-8")
    result = doc_service.extract(path)
    assert '"key": "value"' in result.text


def test_extract_rejects_unsupported_type(tmp_path: Path):
    path = tmp_path / "binary.exe"
    path.write_bytes(b"\x00\x01")
    with pytest.raises(doc_service.UnsupportedDocument):
        doc_service.extract(path)


def test_extract_truncates_large_text(tmp_path: Path):
    path = tmp_path / "big.txt"
    path.write_text("x" * (doc_service.MAX_EXTRACT_CHARS + 5000), encoding="utf-8")
    result = doc_service.extract(path)
    assert result.truncated is True
    assert len(result.text) == doc_service.MAX_EXTRACT_CHARS


def test_excerpt_is_flat_and_short():
    text = "line one\n\nline two   with   spaces"
    out = doc_service.excerpt(text, limit=20)
    assert "\n" not in out
    assert len(out) <= 21  # 20 chars plus the ellipsis


# --- Memory ---------------------------------------------------------------
def _memory(content: str, kind: str = "fact") -> dict:
    from datetime import datetime, timezone

    return {
        "content": content,
        "kind": kind,
        "created_at": datetime.now(timezone.utc),
    }


def test_score_memory_rewards_overlap():
    query = memory_service._tokens("What database does the project use?")
    relevant = memory_service.score_memory(
        _memory("The project uses MongoDB for persistence"), query
    )
    irrelevant = memory_service.score_memory(
        _memory("Likes jazz and long walks"), query
    )
    assert relevant > irrelevant


def test_score_memory_handles_empty_query():
    assert memory_service.score_memory(_memory("anything"), set()) == 0.0


def test_render_formats_memories():
    block = memory_service.render(
        [_memory("Prefers concise answers", "preference")]
    )
    assert "Known facts about this user:" in block
    assert "(preference) Prefers concise answers" in block


def test_render_empty_returns_empty_string():
    assert memory_service.render([]) == ""
