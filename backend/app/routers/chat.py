from fastapi import APIRouter, Depends, HTTPException
from app.database import supabase
from app.auth import get_current_user, CurrentUser
from app.models.schemas import ChatRequest, ChatResponse
from app.services.agent import run_agent

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def chat(payload: ChatRequest, user: CurrentUser = Depends(get_current_user)):
    session_id = payload.session_id
    if session_id:
        session = supabase.table("chat_sessions").select("*").eq("id", session_id).maybe_single().execute().data
        if not session or session["user_id"] != user.id:
            raise HTTPException(403, "Not your chat session")
    else:
        session = supabase.table("chat_sessions").insert(
            {"user_id": user.id, "title": payload.message[:60]}
        ).execute().data[0]
        session_id = session["id"]

    history_rows = (
        supabase.table("chat_messages")
        .select("role, content")
        .eq("session_id", session_id)
        .order("created_at")
        .execute()
        .data
    )
    history = [{"role": r["role"], "content": r["content"]} for r in history_rows if r["role"] in ("user", "assistant")]

    supabase.table("chat_messages").insert(
        {"session_id": session_id, "role": "user", "content": payload.message}
    ).execute()

    result = run_agent(user.id, payload.message, history=history)

    supabase.table("chat_messages").insert(
        {"session_id": session_id, "role": "assistant", "content": result["reply"]}
    ).execute()

    return ChatResponse(
        session_id=session_id,
        reply=result["reply"],
        actions_taken=result["actions_taken"],
        sources=result["sources"],
        agents_used=result["agents_used"],
    )


@router.get("/sessions")
def list_sessions(user: CurrentUser = Depends(get_current_user)):
    return supabase.table("chat_sessions").select("*").eq("user_id", user.id).order("created_at", desc=True).execute().data


@router.get("/sessions/{session_id}/messages")
def get_messages(session_id: str, user: CurrentUser = Depends(get_current_user)):
    session = supabase.table("chat_sessions").select("user_id").eq("id", session_id).maybe_single().execute().data
    if not session or session["user_id"] != user.id:
        raise HTTPException(403, "Not your chat session")
    return supabase.table("chat_messages").select("*").eq("session_id", session_id).order("created_at").execute().data
