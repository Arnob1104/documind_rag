# DocuMind — AI Knowledge Base

A markdown knowledge base with PDF import, tags, version history, semantic search, and a multi-agent AI assistant (LangGraph supervisor + retriever and tagger agents) that can search, read and tag your documents.

Chat with documents: plain-language Q&A grounded in the user’s own documents, with source citations.
• **Multi-agent assistant**: a supervisor routes each request to a retriever agent or a tagger agent, then a responder writes
the reply.
• **Semantic search & PDF upload**by meaning, ranked by similarity with exact title matches; PDFs are extracted and
indexed.
• **Editor experience**: Markdown editor with live preview and auto-save, tags with AI tagging, public/private documents,
and version history snapshots.
Tools: Next.js, React.js, Tailwind CSS, FastAPI, LangGraph, RAG, pgvector, PostgreSQL, Groq
