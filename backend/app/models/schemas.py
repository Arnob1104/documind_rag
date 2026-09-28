from pydantic import BaseModel
from datetime import datetime


class DocumentCreate(BaseModel):
    title: str
    content: str = ""
    excerpt: str | None = None
    is_public: bool = False


class DocumentUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    excerpt: str | None = None
    is_public: bool | None = None


class DocumentOut(BaseModel):
    id: str
    title: str
    content: str
    excerpt: str | None
    is_public: bool
    author_id: str
    created_at: datetime
    updated_at: datetime


class TagCreate(BaseModel):
    name: str
    color: str | None = None


class SearchResultOut(BaseModel):
    document_id: str
    title: str
    excerpt: str | None
    snippet: str
    score: float
    source: str  # "vector" | "keyword"


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    actions_taken: list[str] = []
    sources: list[dict] = []
    agents_used: list[str] = []
