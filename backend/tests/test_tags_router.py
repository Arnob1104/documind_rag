def test_create_and_list_tags(app_client, auth_headers):
    resp = app_client.post("/api/tags", json={"name": "Research", "color": "#fff"}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["name"] == "research"  # lowercased

    tags = app_client.get("/api/tags").json()
    assert any(t["name"] == "research" for t in tags)


def test_create_duplicate_tag_returns_existing(app_client, auth_headers):
    r1 = app_client.post("/api/tags", json={"name": "dup"}, headers=auth_headers).json()
    r2 = app_client.post("/api/tags", json={"name": "dup"}, headers=auth_headers).json()
    assert r1["id"] == r2["id"]


def test_attach_and_detach_tag_requires_ownership(app_client, auth_headers, other_auth_headers):
    doc = app_client.post("/api/documents", json={"title": "Doc"}, headers=auth_headers).json()
    tag = app_client.post("/api/tags", json={"name": "urgent"}, headers=auth_headers).json()

    forbidden = app_client.post(f"/api/tags/documents/{doc['id']}/{tag['id']}", headers=other_auth_headers)
    assert forbidden.status_code == 403

    ok = app_client.post(f"/api/tags/documents/{doc['id']}/{tag['id']}", headers=auth_headers)
    assert ok.status_code == 200

    detach_forbidden = app_client.delete(f"/api/tags/documents/{doc['id']}/{tag['id']}", headers=other_auth_headers)
    assert detach_forbidden.status_code == 403

    detach_ok = app_client.delete(f"/api/tags/documents/{doc['id']}/{tag['id']}", headers=auth_headers)
    assert detach_ok.status_code == 200
