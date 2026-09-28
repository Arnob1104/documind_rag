"""
Regression tests for the issues reported against the first backend cut.
Each test is named after the problem it guards.
"""
import io
from datetime import datetime, timedelta, timezone

from reportlab.pdfgen import canvas


def _pdf(text):
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(72, 800, text)
    c.save()
    return buf.getvalue()


def _chunks_text(fake_db, doc_id):
    return " ".join(c["content"] for c in fake_db.db.get("document_chunks", []) if c["document_id"] == doc_id)


# ── 1. Version history must be owner-only ────────────────────────────────────
def test_versions_hidden_from_other_signed_in_users(app_client, auth_headers, other_auth_headers):
    doc = app_client.post("/api/documents", json={"title": "Private", "content": "v1"}, headers=auth_headers).json()
    app_client.patch(f"/api/documents/{doc['id']}", json={"content": "v2 secret"}, headers=auth_headers)

    assert app_client.get(f"/api/documents/{doc['id']}/versions", headers=other_auth_headers).status_code == 403
    assert app_client.get(f"/api/documents/{doc['id']}/versions", headers=auth_headers).status_code == 200


def test_versions_of_public_doc_still_owner_only(app_client, auth_headers, other_auth_headers):
    # History can contain text the author deliberately removed before publishing.
    doc = app_client.post(
        "/api/documents", json={"title": "Pub", "content": "draft", "is_public": True}, headers=auth_headers
    ).json()
    app_client.patch(f"/api/documents/{doc['id']}", json={"content": "final"}, headers=auth_headers)
    assert app_client.get(f"/api/documents/{doc['id']}/versions", headers=other_auth_headers).status_code == 403


def test_versions_requires_auth_and_404s_for_missing_doc(app_client, auth_headers):
    assert app_client.get("/api/documents/whatever/versions").status_code == 401
    assert app_client.get("/api/documents/does-not-exist/versions", headers=auth_headers).status_code == 404


# ── 2. Tag deletion must be owner-only ───────────────────────────────────────
def test_only_creator_can_delete_tag(app_client, auth_headers, other_auth_headers, fake_db):
    tag = app_client.post("/api/tags", json={"name": "mine"}, headers=auth_headers).json()
    assert tag["created_by"] == "user-1"

    assert app_client.delete(f"/api/tags/{tag['id']}", headers=other_auth_headers).status_code == 403
    assert any(t["id"] == tag["id"] for t in fake_db.db["tags"])  # still there

    assert app_client.delete(f"/api/tags/{tag['id']}", headers=auth_headers).status_code == 200
    assert not any(t["id"] == tag["id"] for t in fake_db.db["tags"])


def test_delete_missing_tag_is_404(app_client, auth_headers):
    assert app_client.delete("/api/tags/nope", headers=auth_headers).status_code == 404


def test_delete_tag_requires_auth(app_client, auth_headers):
    tag = app_client.post("/api/tags", json={"name": "x"}, headers=auth_headers).json()
    assert app_client.delete(f"/api/tags/{tag['id']}").status_code == 401


def test_tag_in_use_by_someone_elses_document_cannot_be_deleted(app_client, auth_headers, other_auth_headers):
    # Deleting a tag cascades to document_tags, which would silently strip it
    # from other people's documents.
    tag = app_client.post("/api/tags", json={"name": "shared"}, headers=auth_headers).json()
    theirs = app_client.post("/api/documents", json={"title": "Theirs"}, headers=other_auth_headers).json()
    assert app_client.post(f"/api/tags/documents/{theirs['id']}/{tag['id']}", headers=other_auth_headers).status_code == 200

    resp = app_client.delete(f"/api/tags/{tag['id']}", headers=auth_headers)
    assert resp.status_code == 409


def test_legacy_tag_without_owner_cannot_be_deleted(app_client, auth_headers, fake_db):
    fake_db.table("tags").insert({"id": "legacy", "name": "legacy"}).execute()
    assert app_client.delete("/api/tags/legacy", headers=auth_headers).status_code == 403


# ── 3. PDF text must survive an edit ─────────────────────────────────────────
def _doc_with_pdf(app_client, auth_headers, phrase="zeppelin airship ballast tables"):
    doc = app_client.post("/api/documents", json={"title": "PDF doc", "content": "intro"}, headers=auth_headers).json()
    r = app_client.post(
        "/api/upload/pdf",
        data={"document_id": doc["id"]},
        files={"file": ("r.pdf", _pdf(phrase), "application/pdf")},
        headers=auth_headers,
    )
    assert r.status_code == 200
    return doc, phrase


def test_pdf_text_still_indexed_after_content_edit(app_client, auth_headers, fake_db):
    doc, phrase = _doc_with_pdf(app_client, auth_headers)
    assert "zeppelin" in _chunks_text(fake_db, doc["id"])

    app_client.patch(f"/api/documents/{doc['id']}", json={"content": "intro, edited"}, headers=auth_headers)

    text = _chunks_text(fake_db, doc["id"])
    assert "edited" in text
    assert "zeppelin" in text, "PDF text was dropped from the index by an edit"


def test_pdf_text_still_indexed_after_title_edit(app_client, auth_headers, fake_db):
    doc, _ = _doc_with_pdf(app_client, auth_headers)
    app_client.patch(f"/api/documents/{doc['id']}", json={"title": "Renamed"}, headers=auth_headers)
    text = _chunks_text(fake_db, doc["id"])
    assert "Renamed" in text and "zeppelin" in text


def test_pdf_text_not_double_indexed_when_frontend_also_appended_it(app_client, auth_headers, fake_db):
    # The current frontend appends the extracted text to the body as well.
    doc, phrase = _doc_with_pdf(app_client, auth_headers)
    body = "intro\n\n## Extracted from PDF\n\n" + phrase
    app_client.patch(f"/api/documents/{doc['id']}", json={"content": body}, headers=auth_headers)
    assert _chunks_text(fake_db, doc["id"]).count("zeppelin") == 1


def test_visibility_toggle_does_not_reindex(app_client, auth_headers, fake_db, monkeypatch):
    doc = app_client.post("/api/documents", json={"title": "T", "content": "c"}, headers=auth_headers).json()
    calls = []
    monkeypatch.setattr("app.routers.documents.index_document", lambda *a, **k: calls.append(a))
    app_client.patch(f"/api/documents/{doc['id']}", json={"is_public": True}, headers=auth_headers)
    assert calls == []


def test_empty_patch_is_a_noop_not_a_500(app_client, auth_headers):
    doc = app_client.post("/api/documents", json={"title": "T"}, headers=auth_headers).json()
    resp = app_client.patch(f"/api/documents/{doc['id']}", json={}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["title"] == "T"


# ── 4. Auto-save must not create a version per keystroke-pause ───────────────
def _versions(fake_db, doc_id):
    return [v for v in fake_db.db.get("document_versions", []) if v["document_id"] == doc_id]


def test_rapid_autosaves_create_a_single_version(app_client, auth_headers, fake_db):
    doc = app_client.post("/api/documents", json={"title": "T", "content": "v0"}, headers=auth_headers).json()
    for i in range(1, 8):
        r = app_client.patch(f"/api/documents/{doc['id']}", json={"content": f"v{i}"}, headers=auth_headers)
        assert r.status_code == 200
    versions = _versions(fake_db, doc["id"])
    assert len(versions) == 1
    assert versions[0]["content"] == "v0"  # the state before the editing burst began


def test_new_version_after_interval_elapses(app_client, auth_headers, fake_db):
    doc = app_client.post("/api/documents", json={"title": "T", "content": "v0"}, headers=auth_headers).json()
    app_client.patch(f"/api/documents/{doc['id']}", json={"content": "v1"}, headers=auth_headers)
    app_client.patch(f"/api/documents/{doc['id']}", json={"content": "v2"}, headers=auth_headers)
    assert len(_versions(fake_db, doc["id"])) == 1

    # pretend the last snapshot was taken a while ago
    old = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    for v in _versions(fake_db, doc["id"]):
        v["created_at"] = old

    app_client.patch(f"/api/documents/{doc['id']}", json={"content": "v3"}, headers=auth_headers)
    contents = [v["content"] for v in _versions(fake_db, doc["id"])]
    assert len(contents) == 2 and "v2" in contents


def test_no_version_when_content_unchanged(app_client, auth_headers, fake_db):
    doc = app_client.post("/api/documents", json={"title": "T", "content": "same"}, headers=auth_headers).json()
    app_client.patch(f"/api/documents/{doc['id']}", json={"content": "same"}, headers=auth_headers)
    app_client.patch(f"/api/documents/{doc['id']}", json={"title": "New title"}, headers=auth_headers)
    app_client.patch(f"/api/documents/{doc['id']}", json={"is_public": True}, headers=auth_headers)
    assert _versions(fake_db, doc["id"]) == []


def test_restore_flow_still_produces_a_restorable_version(app_client, auth_headers):
    doc = app_client.post("/api/documents", json={"title": "T", "content": "original"}, headers=auth_headers).json()
    app_client.patch(f"/api/documents/{doc['id']}", json={"content": "changed"}, headers=auth_headers)
    versions = app_client.get(f"/api/documents/{doc['id']}/versions", headers=auth_headers).json()
    assert [v["content"] for v in versions] == ["original"]
