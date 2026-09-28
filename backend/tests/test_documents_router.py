def test_create_document_requires_auth(app_client):
    resp = app_client.post("/api/documents", json={"title": "T", "content": "C"})
    assert resp.status_code == 401


def test_create_and_get_document(app_client, auth_headers):
    resp = app_client.post("/api/documents", json={"title": "My Doc", "content": "Hello world"}, headers=auth_headers)
    assert resp.status_code == 200
    doc = resp.json()
    assert doc["title"] == "My Doc"
    assert doc["author_id"] == "user-1"

    got = app_client.get(f"/api/documents/{doc['id']}", headers=auth_headers)
    assert got.status_code == 200
    assert got.json()["title"] == "My Doc"


def test_create_document_indexes_chunks_for_rag(app_client, auth_headers, fake_db):
    resp = app_client.post(
        "/api/documents",
        json={"title": "Rockets", "content": "Rocket engines produce thrust."},
        headers=auth_headers,
    )
    doc_id = resp.json()["id"]
    chunks = [c for c in fake_db.db.get("document_chunks", []) if c["document_id"] == doc_id]
    assert len(chunks) >= 1


def test_private_document_hidden_from_other_users(app_client, auth_headers, other_auth_headers):
    resp = app_client.post(
        "/api/documents",
        json={"title": "Private", "content": "secret", "is_public": False},
        headers=auth_headers,
    )
    doc_id = resp.json()["id"]

    # owner can see it
    assert app_client.get(f"/api/documents/{doc_id}", headers=auth_headers).status_code == 200
    # another authenticated user cannot
    assert app_client.get(f"/api/documents/{doc_id}", headers=other_auth_headers).status_code == 403
    # anonymous cannot
    assert app_client.get(f"/api/documents/{doc_id}").status_code == 403


def test_public_document_visible_to_anonymous(app_client, auth_headers):
    resp = app_client.post(
        "/api/documents",
        json={"title": "Public", "content": "hi", "is_public": True},
        headers=auth_headers,
    )
    doc_id = resp.json()["id"]
    assert app_client.get(f"/api/documents/{doc_id}").status_code == 200


def test_list_documents_filters_by_visibility(app_client, auth_headers, other_auth_headers):
    app_client.post("/api/documents", json={"title": "Mine private", "is_public": False}, headers=auth_headers)
    app_client.post("/api/documents", json={"title": "Mine public", "is_public": True}, headers=auth_headers)

    mine = app_client.get("/api/documents", headers=auth_headers).json()
    titles = {d["title"] for d in mine}
    assert {"Mine private", "Mine public"}.issubset(titles)

    others_view = app_client.get("/api/documents", headers=other_auth_headers).json()
    other_titles = {d["title"] for d in others_view}
    assert "Mine public" in other_titles
    assert "Mine private" not in other_titles


def test_update_document_creates_version_and_reindexes(app_client, auth_headers, fake_db):
    doc = app_client.post("/api/documents", json={"title": "V1", "content": "old content"}, headers=auth_headers).json()

    resp = app_client.patch(f"/api/documents/{doc['id']}", json={"content": "new content entirely"}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["content"] == "new content entirely"

    versions = app_client.get(f"/api/documents/{doc['id']}/versions", headers=auth_headers).json()
    assert any(v["content"] == "old content" for v in versions)

    chunks = [c for c in fake_db.db.get("document_chunks", []) if c["document_id"] == doc["id"]]
    assert any("new content" in c["content"] for c in chunks)


def test_update_document_forbidden_for_non_author(app_client, auth_headers, other_auth_headers):
    doc = app_client.post("/api/documents", json={"title": "Mine"}, headers=auth_headers).json()
    resp = app_client.patch(f"/api/documents/{doc['id']}", json={"title": "Hijacked"}, headers=other_auth_headers)
    assert resp.status_code == 403


def test_get_nonexistent_document_returns_404_not_500(app_client, auth_headers):
    # Regression test: .single() on zero matching rows raises in real
    # postgrest-py rather than returning None — routes must use
    # .maybe_single() so a missing id cleanly 404s instead of 500ing.
    resp = app_client.get("/api/documents/does-not-exist", headers=auth_headers)
    assert resp.status_code == 404


def test_delete_document_only_by_author(app_client, auth_headers, other_auth_headers):
    doc = app_client.post("/api/documents", json={"title": "ToDelete"}, headers=auth_headers).json()
    assert app_client.delete(f"/api/documents/{doc['id']}", headers=other_auth_headers).status_code == 403
    assert app_client.delete(f"/api/documents/{doc['id']}", headers=auth_headers).status_code == 200
    assert app_client.get(f"/api/documents/{doc['id']}", headers=auth_headers).status_code == 404
