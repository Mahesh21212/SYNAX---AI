"""End-to-end smoke test against a running SYNAX API.

Exercises the real stack: MongoDB persistence, document extraction, memory
ranking, conversation CRUD, and the error paths. Chat itself needs an
OpenRouter key, so it is checked for a clean, readable failure when absent.

Usage:
    python scripts/smoke.py [http://127.0.0.1:8000]
"""

from __future__ import annotations

import sys
from pathlib import Path

import httpx

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
PDF = Path(__file__).resolve().parents[1] / "tests" / "sample_smoke.pdf"

passed: list[str] = []
failed: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        passed.append(name)
        print(f"  PASS  {name}")
    else:
        failed.append(f"{name} — {detail}")
        print(f"  FAIL  {name}  {detail}")


def main() -> int:
    with httpx.Client(base_url=BASE, timeout=60.0) as client:
        print("\n[1] health")
        health = client.get("/health").json()
        check("health responds", health.get("status") in {"ok", "degraded"})
        check("database connected", health.get("database") is True, str(health))

        print("\n[2] conversation CRUD")
        created = client.post("/api/conversations", json={"title": "Smoke test"}).json()
        conv_id = created.get("id")
        check("conversation created", bool(conv_id), str(created))
        check("default model set", bool(created.get("model")))

        listed = client.get("/api/conversations").json()
        check("conversation appears in list", any(c["id"] == conv_id for c in listed))

        renamed = client.patch(
            f"/api/conversations/{conv_id}", json={"title": "Renamed", "pinned": True}
        ).json()
        check("rename applied", renamed.get("title") == "Renamed", str(renamed))
        check("pin applied", renamed.get("pinned") is True)

        messages = client.get(f"/api/conversations/{conv_id}/messages").json()
        check("new conversation has no messages", messages == [])

        print("\n[3] memory")
        mem = client.post(
            "/api/memory",
            json={"content": "Prefers concise answers.", "kind": "preference"},
        ).json()
        check("memory created", bool(mem.get("id")), str(mem))
        memories = client.get("/api/memory").json()
        check("memory listed", any(m["id"] == mem["id"] for m in memories))
        deleted = client.delete(f"/api/memory/{mem['id']}")
        check("memory deleted", deleted.status_code == 204, str(deleted.status_code))

        print("\n[4] document upload and extraction")
        if PDF.exists():
            with PDF.open("rb") as handle:
                upload = client.post(
                    "/api/documents",
                    files={"file": (PDF.name, handle, "application/pdf")},
                )
            check("pdf accepted", upload.status_code == 201, upload.text[:200])
            if upload.status_code == 201:
                doc = upload.json()
                check("pdf text extracted", doc.get("char_count", 0) > 0, str(doc))
                check("pdf page count read", doc.get("pages") == 1, str(doc.get("pages")))
                check("excerpt present", bool(doc.get("excerpt")))
                docs = client.get("/api/documents").json()
                check("document listed", any(d["id"] == doc["id"] for d in docs))
                removed = client.delete(f"/api/documents/{doc['id']}")
                check("document deleted", removed.status_code == 204)
        else:
            check("sample pdf present", False, f"missing {PDF}")

        print("\n[5] error handling")
        bad_upload = client.post(
            "/api/documents",
            files={"file": ("bad.exe", b"\x00\x01", "application/octet-stream")},
        )
        check("unsupported type rejected", bad_upload.status_code == 415)

        bad_id = client.get("/api/conversations/not-an-id")
        check("bad id rejected", bad_id.status_code == 400, str(bad_id.status_code))

        missing = client.get("/api/conversations/6af4620399376ab72e8221ff")
        check("missing conversation 404s", missing.status_code == 404)

        empty = client.post("/api/chat", json={"message": ""})
        check("empty message rejected", empty.status_code == 422)

        print("\n[6] chat path")
        chat = client.post(
            "/api/chat",
            json={"message": "Say hello in one word.", "conversation_id": conv_id},
        )
        if chat.status_code == 200:
            body = chat.json()
            check("chat answered", bool(body["message"]["content"]))
            check("agent trace returned", len(body.get("steps", [])) > 0)
        elif chat.status_code == 503:
            detail = chat.json().get("detail", "")
            check(
                "chat fails cleanly without a key",
                "OPENROUTER_API_KEY" in detail or "OpenRouter" in detail,
                detail[:160],
            )
        else:
            check("chat returned a known status", False, f"{chat.status_code} {chat.text[:160]}")

        print("\n[7] model catalogue")
        models = client.get("/api/models").json()
        check("models returned", len(models.get("models", [])) > 0)

        print("\n[8] cleanup")
        gone = client.delete(f"/api/conversations/{conv_id}")
        check("conversation deleted", gone.status_code == 204)

    print("\n" + "=" * 60)
    print(f"PASSED: {len(passed)}   FAILED: {len(failed)}")
    for failure in failed:
        print(f"  - {failure}")
    print("=" * 60)
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
