from app.database import supabase
from app.services.embeddings import embed_texts, embed_query
from app.config import settings


def chunk_text(text: str, size: int = settings.CHUNK_SIZE, overlap: int = settings.CHUNK_OVERLAP) -> list[str]:
    text = text.strip()
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = start + size
        chunks.append(text[start:end])
        start = end - overlap
        if start < 0:
            break
    return [c.strip() for c in chunks if c.strip()]


def build_index_text(title: str, content: str, pdf_text: str | None = None) -> str:
    """
    The single definition of "what text represents a document in the index":
    title + body + extracted PDF text.

    Every write path (create, edit, PDF upload) must build the text through here.
    Before this existed, edits indexed only title + body and silently dropped the
    PDF text from search.

    The frontend also appends the extracted text to the body on upload; if the
    body already contains it we don't add it a second time.
    """
    parts = [title or "", content or ""]
    pdf_text = (pdf_text or "").strip()
    if pdf_text and pdf_text not in (content or ""):
        parts.append(pdf_text)
    return "\n\n".join(parts)


def reindex_document(document_id: str, title: str, content: str) -> int:
    """Re-index a document, pulling in its stored PDF text (if any)."""
    rows = supabase.table("pdf_data").select("extracted_text").eq("document_id", document_id).execute().data
    pdf_text = rows[0]["extracted_text"] if rows else None
    return index_document(document_id, build_index_text(title, content, pdf_text))


def index_document(document_id: str, text: str) -> int:
    """
    (Re)chunks + embeds a document's full text (content + any extracted PDF text)
    and stores it in document_chunks. Call this after create/update/PDF-upload.
    """
    # wipe old chunks for this document, then re-insert
    supabase.table("document_chunks").delete().eq("document_id", document_id).execute()

    chunks = chunk_text(text)
    if not chunks:
        return 0

    vectors = embed_texts(chunks)
    rows = [
        {
            "document_id": document_id,
            "chunk_index": i,
            "content": chunk,
            "embedding": vector,
        }
        for i, (chunk, vector) in enumerate(zip(chunks, vectors))
    ]
    supabase.table("document_chunks").insert(rows).execute()
    return len(rows)


def retrieve_relevant_chunks(query: str, user_id: str | None, top_k: int = 6) -> list[dict]:
    """
    Vector similarity search scoped to documents the user may see
    (public docs, or their own). Uses the match_document_chunks() SQL
    function defined in supabase/schema.sql.
    """
    query_vector = embed_query(query)
    result = supabase.rpc(
        "match_document_chunks",
        {
            "query_embedding": query_vector,
            "match_count": top_k,
            "requesting_user_id": user_id,
        },
    ).execute()
    return result.data or []
