import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from app.config import settings
from app.database import supabase
from app.auth import get_current_user, get_optional_user, CurrentUser
from app.models.schemas import DocumentCreate, DocumentUpdate
from app.services.rag import index_document, reindex_document

router = APIRouter(prefix="/api/documents", tags=["documents"])


def _parse_ts(value: str) -> datetime:
    """Parse a Postgres timestamptz string (may have 1-6 fractional digits or 'Z')."""
    value = value.strip().replace("Z", "+00:00")
    # normalise fractional seconds to 6 digits so fromisoformat accepts them on every Python version
    value = re.sub(r"\.(\d+)", lambda m: "." + m.group(1).ljust(6, "0")[:6], value)
    dt = datetime.fromisoformat(value)
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _get_owned_document(document_id: str, user: CurrentUser, action: str) -> dict:
    doc = supabase.table("documents").select("*").eq("id", document_id).maybe_single().execute().data
    if not doc:
        raise HTTPException(404, "Document not found")
    if doc["author_id"] != user.id:
        raise HTTPException(403, f"Only the author can {action}")
    return doc


def _should_snapshot(document_id: str, previous_content: str, new_content: str) -> bool:
    """
    Auto-save PATCHes every couple of seconds. Snapshot the *previous* content only
    when the body really changes and the newest snapshot is older than
    VERSION_MIN_INTERVAL_SECONDS, so one editing burst = one restore point.
    """
    if new_content == previous_content:
        return False
    latest = (
        supabase.table("document_versions")
        .select("content, created_at")
        .eq("document_id", document_id)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
        .data
    )
    if not latest:
        return True
    if latest[0]["content"] == previous_content:
        return False
    age = (datetime.now(timezone.utc) - _parse_ts(latest[0]["created_at"])).total_seconds()
    return age >= settings.VERSION_MIN_INTERVAL_SECONDS


@router.get("")
def list_documents(user: CurrentUser | None = Depends(get_optional_user)):
    query = supabase.table("documents").select("*, tags:document_tags(tag:tags(*))")
    if user:
        query = query.or_(f"is_public.eq.true,author_id.eq.{user.id}")
    else:
        query = query.eq("is_public", True)
    return query.order("updated_at", desc=True).execute().data


@router.post("")
def create_document(payload: DocumentCreate, user: CurrentUser = Depends(get_current_user)):
    row = payload.model_dump()
    row["author_id"] = user.id
    created = supabase.table("documents").insert(row).execute().data[0]
    index_document(created["id"], f"{created['title']}\n\n{created['content']}")
    return created


@router.get("/{document_id}")
def get_document(document_id: str, user: CurrentUser | None = Depends(get_optional_user)):
    doc = supabase.table("documents").select("*, tags:document_tags(tag:tags(*)), pdf_data(*)").eq("id", document_id).maybe_single().execute().data
    if not doc:
        raise HTTPException(404, "Document not found")
    if not doc["is_public"] and (not user or doc["author_id"] != user.id):
        raise HTTPException(403, "Not authorized to view this document")
    return doc


@router.patch("/{document_id}")
def update_document(document_id: str, payload: DocumentUpdate, user: CurrentUser = Depends(get_current_user)):
    existing = _get_owned_document(document_id, user, "edit this document")

    updates = payload.model_dump(exclude_unset=True)
    # title / content / is_public are NOT NULL columns: treat an explicit null as "leave unchanged"
    updates = {k: v for k, v in updates.items() if v is not None or k == "excerpt"}
    if not updates:
        return existing

    if "content" in updates:
        if _should_snapshot(document_id, existing["content"], updates["content"]):
            supabase.table("document_versions").insert(
                {"document_id": document_id, "content": existing["content"]}
            ).execute()

    updated = supabase.table("documents").update(updates).eq("id", document_id).execute().data[0]

    # Only title/body affect the index. reindex_document also folds in the stored
    # PDF text, so an edit no longer drops it from search.
    if "content" in updates or "title" in updates:
        reindex_document(document_id, updated["title"], updated["content"])
    return updated


@router.delete("/{document_id}")
def delete_document(document_id: str, user: CurrentUser = Depends(get_current_user)):
    _get_owned_document(document_id, user, "delete this document")
    supabase.table("documents").delete().eq("id", document_id).execute()
    return {"deleted": True}


@router.get("/{document_id}/versions")
def list_versions(document_id: str, user: CurrentUser = Depends(get_current_user)):
    # Owner only — even for public documents. History can contain text the
    # author removed on purpose before (or after) publishing.
    _get_owned_document(document_id, user, "view this document's version history")
    return (
        supabase.table("document_versions")
        .select("*")
        .eq("document_id", document_id)
        .order("created_at", desc=True)
        .execute()
        .data
    )
