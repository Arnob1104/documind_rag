# DocuMind FastAPI Backend (Supabase + Groq RAG Agent)

This is the backend of the merged DocuMind project (see the top-level README).
It replaces the old Next.js API routes + Prisma/Neon backend; the frontend in
`../frontend` talks to it over HTTP.

## 1. Supabase setup
1. Create a project at supabase.com.
2. In the SQL editor, run `supabase/schema.sql` (creates tables, `pgvector`, RLS policies, and the `match_document_chunks` search function).
3. In Project Settings → API, copy: `Project URL` and the `service_role` key.
   (Already ran an older `schema.sql`? Run `supabase/migrations/001_tag_owner_and_version_privacy.sql` — idempotent.)
4. In Authentication → Providers, enable Email (or whichever providers you want) — this replaces NextAuth.

## 2. Backend setup
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in Supabase + Groq values
uvicorn main:app --reload --port 8000
```
Get a free Groq API key at console.groq.com.

## 3. How the agent/RAG pipeline works
- On every document create/update and PDF upload, `services/rag.py` chunks the
  text and embeds it locally with `sentence-transformers` (`all-MiniLM-L6-v2`,
  free, no external API), storing vectors in `document_chunks` (pgvector).
- `POST /api/chat` runs a **LangGraph multi-agent team** (`services/agent.py`)
  on Groq (Llama 3.3 70B):

  ```
  START → supervisor ⇄ {retriever | tagger} → responder → END
  ```

  - **supervisor** routes each request (JSON decision); each specialist runs at most once.
  - **retriever** (read-only): `search_knowledge_base`, `list_documents`, `get_document`.
  - **tagger** (the only writer): `list_my_documents`, `list_tags`, `get_document`, `apply_tags` — owned documents only, reuses existing tags.
  - **responder** passes a lone specialist's answer through, merges two, or answers small talk.

  "Summarize my Q3 notes and tag them" → retriever, then tagger (which sees the retriever's findings), then a merged reply.
  Tool access is an allowlist per agent (`services/agent_tools.py`), and the acting user id comes from the
  authenticated request — never from the model. The response includes `agents_used` for the UI.
- `GET /api/search` blends vector search with a keyword title-match fallback.

## 4. Auth model
The Next.js frontend authenticates directly against Supabase Auth
(`@supabase/supabase-js`) and sends the resulting access token as
`Authorization: Bearer <token>` on every request to this API. `app/auth.py`
asks Supabase Auth (`auth.get_user(token)`) who the token belongs to — so
expiry, revocation and any JWT signing scheme (including asymmetric keys) are
Supabase's concern, not ours. Results are cached per token for
`AUTH_CACHE_TTL_SECONDS` (default 30). No session state lives in FastAPI.

### Authorization rules
- Documents: public → anyone; private → author only. Only the author edits/deletes/tags/attaches PDFs.
- **Version history: author only, even for public documents.**
- **Tags are shared, but only the creator can delete one**, and not while other users' documents use it (409). Legacy tags without a creator can't be deleted via the API.
- Auto-save: a version snapshot is taken only if the body changed *and* the newest snapshot is older than `VERSION_MIN_INTERVAL_SECONDS` (default 600).

## 5. Running the test suite
The tests exercise every router, the RAG chunking/indexing/retrieval pipeline,
the LangGraph multi-agent flow, and Supabase-Auth token handling — against an in-memory
fake Supabase client and a scripted fake Groq client, so **no live Supabase
project or Groq key is needed to run them.**

```bash
pip install -r requirements-dev.txt
pytest -v
```

83 tests, covering: Supabase-Auth token handling (valid / missing / rejected / cached / expired /
revoked), document CRUD + ownership/visibility rules, **regression tests for each reported issue**
(version-history privacy, tag-delete ownership, PDF text surviving edits, auto-save version throttling),
tag rules, PDF upload + extraction (against a real generated PDF) + re-indexing, hybrid search visibility,
RAG chunking and retrieval scoping, the LangGraph flow (routing, single/both specialists, fallbacks on bad
routing or model errors, step caps, per-agent tool allowlists, model-supplied `user_id` ignored), the chat
endpoint, and one end-to-end walkthrough of every feature.

The SQL was additionally checked against a real Postgres 16 + pgvector: fresh install, upgrade from the
original schema with legacy data, idempotent re-run of the migration, RLS policies exercised as two users,
and `match_document_chunks` visibility.

One real bug was caught and fixed during testing: every "fetch one row or
404" lookup originally used `.single()`, which real `postgrest-py` raises an
exception on for zero matching rows (rather than returning `None` as you
might expect) — so a request for a nonexistent document would have 500'd
instead of cleanly 404ing. Fixed by switching those lookups to
`.maybe_single()`, with a regression test locking it in.

## Endpoints
| Method | Path | Notes |
|---|---|---|
| GET/POST | `/api/documents` | list / create |
| GET/PATCH/DELETE | `/api/documents/{id}` | + auto re-indexes on edit |
| GET | `/api/documents/{id}/versions` | version history (author only) |
| GET/POST | `/api/tags`, `DELETE /api/tags/{id}` | delete: creator only |
| POST/DELETE | `/api/tags/documents/{document_id}/{tag_id}` | attach/detach |
| POST | `/api/upload/pdf` | multipart form: `document_id`, `file` |
| GET | `/api/search?q=` | hybrid vector+keyword |
| POST | `/api/chat` | agent chat turn (returns `agents_used`) |
| GET | `/api/chat/sessions`, `/api/chat/sessions/{id}/messages` | history |
