from fastapi import APIRouter, Depends, HTTPException
from app.database import supabase
from app.auth import get_current_user, CurrentUser
from app.models.schemas import TagCreate

router = APIRouter(prefix="/api/tags", tags=["tags"])


@router.get("")
def list_tags():
    return supabase.table("tags").select("*").order("name").execute().data


@router.post("")
def create_tag(payload: TagCreate, user: CurrentUser = Depends(get_current_user)):
    name = payload.name.strip().lower()
    if not name:
        raise HTTPException(422, "Tag name cannot be empty")
    existing = supabase.table("tags").select("*").eq("name", name).execute().data
    if existing:
        return existing[0]
    return supabase.table("tags").insert(
        {"name": name, "color": payload.color, "created_by": user.id}
    ).execute().data[0]


@router.delete("/{tag_id}")
def delete_tag(tag_id: str, user: CurrentUser = Depends(get_current_user)):
    tag = supabase.table("tags").select("*").eq("id", tag_id).maybe_single().execute().data
    if not tag:
        raise HTTPException(404, "Tag not found")
    # Tags are shared across users, so only the creator may delete one.
    # Legacy tags with no recorded creator are undeletable through the API.
    if not tag.get("created_by") or tag["created_by"] != user.id:
        raise HTTPException(403, "Only the user who created this tag can delete it")

    # Deleting a tag cascades to document_tags, which would silently strip it
    # from documents that belong to other people.
    usages = supabase.table("document_tags").select("user_id").eq("tag_id", tag_id).execute().data
    if any(u["user_id"] != user.id for u in usages):
        raise HTTPException(409, "This tag is used on other users' documents and can't be deleted")

    supabase.table("tags").delete().eq("id", tag_id).execute()
    return {"deleted": True}


@router.post("/documents/{document_id}/{tag_id}")
def attach_tag(document_id: str, tag_id: str, user: CurrentUser = Depends(get_current_user)):
    doc = supabase.table("documents").select("author_id").eq("id", document_id).maybe_single().execute().data
    if not doc or doc["author_id"] != user.id:
        raise HTTPException(403, "Only the author can tag this document")
    if not supabase.table("tags").select("id").eq("id", tag_id).maybe_single().execute().data:
        raise HTTPException(404, "Tag not found")
    return supabase.table("document_tags").upsert(
        {"document_id": document_id, "tag_id": tag_id, "user_id": user.id}
    ).execute().data


@router.delete("/documents/{document_id}/{tag_id}")
def detach_tag(document_id: str, tag_id: str, user: CurrentUser = Depends(get_current_user)):
    doc = supabase.table("documents").select("author_id").eq("id", document_id).maybe_single().execute().data
    if not doc or doc["author_id"] != user.id:
        raise HTTPException(403, "Only the author can untag this document")
    supabase.table("document_tags").delete().eq("document_id", document_id).eq("tag_id", tag_id).execute()
    return {"deleted": True}
