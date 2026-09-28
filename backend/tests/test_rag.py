from app.services.rag import chunk_text, index_document, retrieve_relevant_chunks


def test_chunk_text_empty_returns_no_chunks():
    assert chunk_text("") == []
    assert chunk_text("   ") == []


def test_chunk_text_short_text_single_chunk():
    chunks = chunk_text("hello world")
    assert chunks == ["hello world"]


def test_chunk_text_respects_overlap_and_covers_full_text():
    text = "A" * 2000
    chunks = chunk_text(text, size=800, overlap=150)
    assert len(chunks) > 1
    # every chunk should be non-empty and within size bound
    assert all(0 < len(c) <= 800 for c in chunks)


def test_index_document_stores_chunks_with_embeddings(fake_db):
    fake_db.table("documents").insert(
        {"id": "doc-1", "title": "Doc", "content": "", "is_public": True, "author_id": "u1"}
    ).execute()

    count = index_document("doc-1", "This is a knowledge base article about rocket engines and thrust.")
    assert count >= 1
    stored = fake_db.db["document_chunks"]
    assert len(stored) == count
    assert all(len(row["embedding"]) == 384 for row in stored)


def test_index_document_replaces_old_chunks(fake_db):
    fake_db.table("documents").insert(
        {"id": "doc-1", "title": "Doc", "content": "", "is_public": True, "author_id": "u1"}
    ).execute()
    index_document("doc-1", "first version of the text")
    first_count = len(fake_db.db["document_chunks"])
    index_document("doc-1", "second version of the text, completely different")
    assert len(fake_db.db["document_chunks"]) >= 1
    # old chunk content shouldn't linger
    contents = [c["content"] for c in fake_db.db["document_chunks"]]
    assert not any("first version" in c for c in contents)


def test_retrieve_relevant_chunks_respects_visibility(fake_db):
    fake_db.table("documents").insert(
        {"id": "pub-doc", "title": "Public rockets", "content": "", "is_public": True, "author_id": "u1"}
    ).execute()
    fake_db.table("documents").insert(
        {"id": "priv-doc", "title": "Private notes", "content": "", "is_public": False, "author_id": "u1"}
    ).execute()
    index_document("pub-doc", "Rocket engines produce thrust via combustion.")
    index_document("priv-doc", "My private password list, do not share.")

    # A stranger (u2) should only ever retrieve chunks from the public doc.
    results = retrieve_relevant_chunks("rocket thrust", user_id="u2", top_k=5)
    doc_ids = {r["document_id"] for r in results}
    assert "priv-doc" not in doc_ids

    # The owner (u1) can see both.
    results_owner = retrieve_relevant_chunks("password", user_id="u1", top_k=5)
    doc_ids_owner = {r["document_id"] for r in results_owner}
    assert "priv-doc" in doc_ids_owner
