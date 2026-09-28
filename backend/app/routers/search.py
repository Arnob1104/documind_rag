from fastapi import APIRouter, Depends, Query
from app.database import supabase
from app.auth import get_optional_user, CurrentUser
from app.services.rag import retrieve_relevant_chunks

router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("")
def search(q: str = Query(..., min_length=1), limit: int = 20, user: CurrentUser | None = Depends(get_optional_user)):
    user_id = user.id if user else None

    # 1. Semantic (vector) search over chunks
    vector_hits = retrieve_relevant_chunks(q, user_id, top_k=limit)

    # 2. Simple keyword fallback/boost on title, so exact title matches always surface
    kw_query = supabase.table("documents").select("id, title, excerpt, is_public, author_id").ilike("title", f"%{q}%")
    if user_id:
        kw_query = kw_query.or_(f"is_public.eq.true,author_id.eq.{user_id}")
    else:
        kw_query = kw_query.eq("is_public", True)
    keyword_hits = kw_query.limit(limit).execute().data

    seen_doc_ids = set()
    results = []

    for hit in vector_hits:
        if hit["document_id"] in seen_doc_ids:
            continue
        seen_doc_ids.add(hit["document_id"])
        results.append(
            {
                "document_id": hit["document_id"],
                "title": hit["title"],
                "excerpt": None,
                "snippet": hit["content"][:240],
                "score": hit["similarity"],
                "source": "vector",
            }
        )

    for doc in keyword_hits:
        if doc["id"] in seen_doc_ids:
            continue
        seen_doc_ids.add(doc["id"])
        results.append(
            {
                "document_id": doc["id"],
                "title": doc["title"],
                "excerpt": doc.get("excerpt"),
                "snippet": doc.get("excerpt") or "",
                "score": 1.0,
                "source": "keyword",
            }
        )

    return results[:limit]
