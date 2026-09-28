"""
Tools the DocuMind agents can call.

Two rules keep these safe:
  * `user_id` always comes from the authenticated request (graph state) and is
    never a model-supplied argument, so the model can't act as someone else.
  * Every agent gets an explicit allowlist. `execute_tool` refuses anything
    outside it, even if the model hallucinates a tool name.
"""
import json
import logging

from app.database import supabase
from app.services.rag import retrieve_relevant_chunks

logger = logging.getLogger(__name__)

MAX_TOOL_RESULT_CHARS = 6000
MAX_DOC_CHARS = 5000
MAX_TAGS_PER_CALL = 8
MAX_TAG_LEN = 40


# ── Schemas (OpenAI/Groq function-calling format) ────────────────────────────
def _fn(name: str, description: str, properties: dict | None = None, required: list[str] | None = None) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {"type": "object", "properties": properties or {}, "required": required or []},
        },
    }


SCHEMAS: dict[str, dict] = {
    "search_knowledge_base": _fn(
        "search_knowledge_base",
        "Semantic search over the user's visible documents. Use this to find content relevant to a question.",
        {"query": {"type": "string"}},
        ["query"],
    ),
    "list_documents": _fn(
        "list_documents",
        "List the titles and ids of documents visible to the user (own + public), to work out which document they mean.",
    ),
    "get_document": _fn(
        "get_document",
        "Fetch the full text of one document by id, e.g. to summarize it.",
        {"document_id": {"type": "string"}},
        ["document_id"],
    ),
    "list_my_documents": _fn(
        "list_my_documents",
        "List the documents the current user OWNS (only these can be tagged), with the tags each already has.",
    ),
    "list_tags": _fn(
        "list_tags",
        "List all existing tag names. Check this first and reuse an existing tag instead of inventing a near-duplicate.",
    ),
    "apply_tags": _fn(
        "apply_tags",
        "Create (if needed) and attach one or more tags to a document the user owns.",
        {"document_id": {"type": "string"}, "tags": {"type": "array", "items": {"type": "string"}}},
        ["document_id", "tags"],
    ),
}

RETRIEVER_TOOLS = ["search_knowledge_base", "list_documents", "get_document"]
TAGGER_TOOLS = ["list_my_documents", "list_tags", "get_document", "apply_tags"]


def schemas_for(names: list[str]) -> list[dict]:
    return [SCHEMAS[n] for n in names]


# ── Implementations ──────────────────────────────────────────────────────────
def _search_knowledge_base(args: dict, user_id: str) -> dict:
    query = str(args.get("query", "")).strip()
    if not query:
        return {"error": "query is required"}
    return {"results": retrieve_relevant_chunks(query, user_id, top_k=6)}


def _list_documents(args: dict, user_id: str) -> dict:
    res = (
        supabase.table("documents")
        .select("id, title, is_public, author_id")
        .or_(f"is_public.eq.true,author_id.eq.{user_id}")
        .limit(50)
        .execute()
    )
    return {"documents": res.data}


def _get_document(args: dict, user_id: str) -> dict:
    document_id = str(args.get("document_id", ""))
    doc = (
        supabase.table("documents")
        .select("*, pdf_data(extracted_text)")
        .eq("id", document_id)
        .maybe_single()
        .execute()
        .data
    )
    if not doc or not (doc["is_public"] or doc["author_id"] == user_id):
        return {"error": "not found or not visible to this user"}

    content = doc.get("content") or ""
    pdf = doc.get("pdf_data")
    pdf = pdf[0] if isinstance(pdf, list) and pdf else pdf
    pdf_text = (pdf or {}).get("extracted_text") if isinstance(pdf, dict) else None
    if pdf_text and pdf_text.strip() not in content:
        content = f"{content}\n\n[Extracted from attached PDF]\n{pdf_text}"

    truncated = len(content) > MAX_DOC_CHARS
    return {
        "document": {
            "id": doc["id"],
            "title": doc["title"],
            "is_public": doc["is_public"],
            "is_owner": doc["author_id"] == user_id,
            "content": content[:MAX_DOC_CHARS],
            "truncated": truncated,
        }
    }


def _list_my_documents(args: dict, user_id: str) -> dict:
    docs = (
        supabase.table("documents")
        .select("id, title, tags:document_tags(tag:tags(name))")
        .eq("author_id", user_id)
        .limit(50)
        .execute()
        .data
    )
    out = []
    for d in docs:
        names = [t["tag"]["name"] for t in (d.get("tags") or []) if t.get("tag")]
        out.append({"id": d["id"], "title": d["title"], "tags": names})
    return {"documents": out}


def _list_tags(args: dict, user_id: str) -> dict:
    tags = supabase.table("tags").select("name").order("name").execute().data
    return {"tags": [t["name"] for t in tags]}


def _apply_tags(args: dict, user_id: str) -> dict:
    document_id = str(args.get("document_id", ""))
    raw = args.get("tags") or []
    if isinstance(raw, str):
        raw = [raw]

    doc = supabase.table("documents").select("author_id").eq("id", document_id).maybe_single().execute().data
    if not doc or doc["author_id"] != user_id:
        return {"error": "only the document owner can tag it"}

    applied: list[str] = []
    for name in raw[:MAX_TAGS_PER_CALL]:
        name = str(name).strip().lower()[:MAX_TAG_LEN]
        if not name or name in applied:
            continue
        existing = supabase.table("tags").select("id").eq("name", name).execute().data
        if existing:
            tag_id = existing[0]["id"]
        else:
            tag_id = supabase.table("tags").insert({"name": name, "created_by": user_id}).execute().data[0]["id"]
        supabase.table("document_tags").upsert(
            {"document_id": document_id, "tag_id": tag_id, "user_id": user_id}
        ).execute()
        applied.append(name)
    return {"applied_tags": applied}


IMPLS = {
    "search_knowledge_base": _search_knowledge_base,
    "list_documents": _list_documents,
    "get_document": _get_document,
    "list_my_documents": _list_my_documents,
    "list_tags": _list_tags,
    "apply_tags": _apply_tags,
}


def execute_tool(name: str, raw_arguments: str | None, user_id: str, allowed: list[str]) -> dict:
    """Run one tool call on behalf of `user_id`. Never raises: errors go back to the model as data."""
    if name not in allowed or name not in IMPLS:
        return {"error": f"tool '{name}' is not available to this agent"}
    try:
        args = json.loads(raw_arguments or "{}")
        if not isinstance(args, dict):
            raise ValueError("arguments must be a JSON object")
    except (json.JSONDecodeError, ValueError) as exc:
        return {"error": f"invalid tool arguments: {exc}"}
    try:
        return IMPLS[name](args, user_id)
    except Exception as exc:  # DB/embedding hiccup: let the agent explain rather than 500 the whole chat
        logger.exception("agent tool %s failed", name)
        return {"error": f"tool '{name}' failed: {type(exc).__name__}"}


def dump_result(result: dict) -> str:
    text = json.dumps(result, default=str)
    return text if len(text) <= MAX_TOOL_RESULT_CHARS else text[:MAX_TOOL_RESULT_CHARS] + "…[truncated]"
