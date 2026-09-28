"""
One end-to-end walkthrough of every feature, driven through the real FastAPI app
(routing, auth dependency, validation) with in-memory Supabase + scripted Groq.
Two users: alice (owner) and bob (another signed-in user).
"""
import io

from reportlab.pdfgen import canvas

from tests.test_agent_chat import FakeGroq, route, say, tool_call, use


def _pdf(text):
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(72, 800, text)
    c.save()
    return buf.getvalue()


def test_full_product_walkthrough(app_client, auth_headers, other_auth_headers, fake_db, monkeypatch):
    A, B = auth_headers, other_auth_headers

    # health + auth gate
    assert app_client.get("/api/health").json() == {"status": "ok"}
    assert app_client.get("/api/chat/sessions").status_code == 401

    # ── documents: create / read / list ──────────────────────────────────────
    doc = app_client.post("/api/documents", json={"title": "Zeppelin notes", "content": "# Airships\nintro"}, headers=A).json()
    did = doc["id"]
    assert app_client.get(f"/api/documents/{did}", headers=A).status_code == 200
    assert app_client.get(f"/api/documents/{did}", headers=B).status_code == 403  # private
    assert [d["id"] for d in app_client.get("/api/documents", headers=A).json()] == [did]
    assert app_client.get("/api/documents", headers=B).json() == []

    # ── PDF upload -> searchable ─────────────────────────────────────────────
    up = app_client.post(
        "/api/upload/pdf", data={"document_id": did},
        files={"file": ("ballast.pdf", _pdf("hydrogen ballast tables for airships"), "application/pdf")}, headers=A,
    )
    assert up.status_code == 200 and "hydrogen ballast" in up.json()["extracted_text"]
    assert app_client.post(
        "/api/upload/pdf", data={"document_id": did},
        files={"file": ("x.pdf", _pdf("nope"), "application/pdf")}, headers=B,
    ).status_code == 403

    # ── an auto-save burst: many edits, one version, PDF text survives ───────
    for i in range(10):
        r = app_client.patch(f"/api/documents/{did}", json={"content": f"# Airships\nedit {i}"}, headers=A)
        assert r.status_code == 200
    versions = app_client.get(f"/api/documents/{did}/versions", headers=A).json()
    assert [v["content"] for v in versions] == ["# Airships\nintro"]          # 10 saves -> 1 version
    assert app_client.get(f"/api/documents/{did}/versions", headers=B).status_code == 403
    indexed = " ".join(c["content"] for c in fake_db.db["document_chunks"] if c["document_id"] == did)
    assert "edit 9" in indexed and "hydrogen ballast" in indexed             # edit kept PDF text indexed

    # ── search ───────────────────────────────────────────────────────────────
    hits = app_client.get("/api/search", params={"q": "Zeppelin"}, headers=A).json()
    assert any(h["document_id"] == did for h in hits)
    assert not any(h["document_id"] == did for h in app_client.get("/api/search", params={"q": "Zeppelin"}, headers=B).json())
    assert not any(h["document_id"] == did for h in app_client.get("/api/search", params={"q": "Zeppelin"}).json())
    vec = app_client.get("/api/search", params={"q": "ballast"}, headers=A).json()
    assert any(h["document_id"] == did and h["source"] == "vector" for h in vec)

    # ── tags: create / attach / delete rules ─────────────────────────────────
    tag = app_client.post("/api/tags", json={"name": "Aviation", "color": "#3B82F6"}, headers=A).json()
    assert tag["name"] == "aviation" and tag["created_by"] == "user-1"
    assert app_client.post(f"/api/tags/documents/{did}/{tag['id']}", headers=B).status_code == 403
    assert app_client.post(f"/api/tags/documents/{did}/{tag['id']}", headers=A).status_code == 200
    assert app_client.delete(f"/api/tags/{tag['id']}", headers=B).status_code == 403
    assert app_client.delete(f"/api/tags/documents/{did}/{tag['id']}", headers=A).status_code == 200
    assert app_client.delete(f"/api/tags/{tag['id']}", headers=A).status_code == 200
    assert app_client.get("/api/tags").json() == []

    # ── publish: bob can now read the doc but still not its history ──────────
    assert app_client.patch(f"/api/documents/{did}", json={"is_public": True}, headers=A).status_code == 200
    assert app_client.get(f"/api/documents/{did}", headers=B).status_code == 200
    assert app_client.get(f"/api/documents/{did}/versions", headers=B).status_code == 403
    assert app_client.get("/api/search", params={"q": "Zeppelin"}).json()  # anonymous sees public docs

    # ── AI assistant: retriever, tagger, both ────────────────────────────────
    fake = use(monkeypatch, FakeGroq(
        supervisor=[route("retriever"), route("respond"), route("tagger"), route("respond")],
        retriever=[tool_call("search_knowledge_base", {"query": "ballast"}), say("The *Zeppelin notes* doc covers hydrogen ballast tables.")],
        tagger=[tool_call("apply_tags", {"document_id": did, "tags": ["airships", "history"]}), say("Tagged *Zeppelin notes* with airships and history.")],
    ))
    r1 = app_client.post("/api/chat", json={"message": "what do I have on ballast?"}, headers=A).json()
    assert r1["agents_used"] == ["retriever"] and "ballast" in r1["reply"]
    assert any(s["document_id"] == did for s in r1["sources"])

    r2 = app_client.post("/api/chat", json={"message": "tag it", "session_id": r1["session_id"]}, headers=A).json()
    assert r2["session_id"] == r1["session_id"] and r2["agents_used"] == ["tagger"]
    assert {t["name"] for t in fake_db.db["tags"]} == {"airships", "history"}
    assert all(t["created_by"] == "user-1" for t in fake_db.db["tags"])
    msgs = app_client.get(f"/api/chat/sessions/{r1['session_id']}/messages", headers=A).json()
    assert [m["role"] for m in msgs] == ["user", "assistant", "user", "assistant"]
    assert app_client.get(f"/api/chat/sessions/{r1['session_id']}/messages", headers=B).status_code == 403

    # ── delete cascades ──────────────────────────────────────────────────────
    assert app_client.delete(f"/api/documents/{did}", headers=B).status_code == 403
    assert app_client.delete(f"/api/documents/{did}", headers=A).status_code == 200
    assert app_client.get(f"/api/documents/{did}", headers=A).status_code == 404
