"""API surface tests that do not require MongoDB or a provider key.

Routes that touch the database are exercised through the OpenAPI schema and
dependency wiring; the live paths are covered by the smoke script.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root_reports_identity():
    res = client.get("/")
    assert res.status_code == 200
    body = res.json()
    assert body["name"] == "SYNAX AI"
    assert body["docs"] == "/docs"


def test_openapi_exposes_expected_routes():
    schema = client.get("/openapi.json").json()
    paths = schema["paths"]
    for expected in [
        "/api/chat",
        "/api/conversations",
        "/api/documents",
        "/api/memory",
        "/api/models",
        "/health",
    ]:
        assert expected in paths, f"missing route {expected}"


def test_health_endpoint_shape():
    res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert set(body) == {"status", "database", "openrouter", "version"}
    assert body["status"] in {"ok", "degraded"}
    assert isinstance(body["database"], bool)
    assert isinstance(body["openrouter"], bool)


def test_chat_rejects_empty_message():
    res = client.post("/api/chat", json={"message": ""})
    assert res.status_code == 422


def test_chat_rejects_unknown_conversation_id():
    res = client.post(
        "/api/chat",
        json={"message": "hello", "conversation_id": "not-an-object-id"},
    )
    assert res.status_code == 400


def test_conversation_rejects_bad_id():
    res = client.get("/api/conversations/nope")
    assert res.status_code == 400


def test_memory_delete_rejects_bad_id():
    res = client.delete("/api/memory/nope")
    assert res.status_code == 404


def test_documents_rejects_unsupported_upload():
    res = client.post(
        "/api/documents",
        files={"file": ("payload.exe", b"\x00\x01", "application/octet-stream")},
    )
    assert res.status_code == 415
