import io
from reportlab.pdfgen import canvas


def _make_pdf_bytes(text):
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(72, 800, text)
    c.save()
    return buf.getvalue()


def test_upload_pdf_requires_ownership(app_client, auth_headers, other_auth_headers):
    doc = app_client.post("/api/documents", json={"title": "PDF doc"}, headers=auth_headers).json()
    pdf_bytes = _make_pdf_bytes("Quarterly financial results")

    forbidden = app_client.post(
        "/api/upload/pdf",
        data={"document_id": doc["id"]},
        files={"file": ("report.pdf", pdf_bytes, "application/pdf")},
        headers=other_auth_headers,
    )
    assert forbidden.status_code == 403


def test_upload_pdf_extracts_and_indexes(app_client, auth_headers, fake_db):
    doc = app_client.post("/api/documents", json={"title": "PDF doc"}, headers=auth_headers).json()
    pdf_bytes = _make_pdf_bytes("Quarterly financial results are strong")

    resp = app_client.post(
        "/api/upload/pdf",
        data={"document_id": doc["id"]},
        files={"file": ("report.pdf", pdf_bytes, "application/pdf")},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    saved = resp.json()
    assert "Quarterly financial results" in saved["extracted_text"]

    chunks = [c for c in fake_db.db.get("document_chunks", []) if c["document_id"] == doc["id"]]
    assert any("Quarterly financial" in c["content"] for c in chunks)


def test_search_finds_document_by_title_keyword(app_client, auth_headers):
    app_client.post("/api/documents", json={"title": "Rocket Propulsion Notes", "content": "..."}, headers=auth_headers)
    resp = app_client.get("/api/search", params={"q": "Rocket"}, headers=auth_headers)
    assert resp.status_code == 200
    results = resp.json()
    assert any("Rocket" in r["title"] for r in results)


def test_search_excludes_private_docs_for_others(app_client, auth_headers, other_auth_headers):
    app_client.post("/api/documents", json={"title": "Confidential Salary Data", "is_public": False}, headers=auth_headers)
    resp = app_client.get("/api/search", params={"q": "Confidential"}, headers=other_auth_headers)
    titles = [r["title"] for r in resp.json()]
    assert "Confidential Salary Data" not in titles
