# DocuMind — AI Knowledge Base

A markdown knowledge base with PDF import, tags, version history, semantic search, and a multi-agent AI assistant (LangGraph supervisor + retriever and tagger agents) that can search, read and tag your documents.

```
documind/
├── frontend/   Next.js 13 UI (Tailwind, shadcn/ui) — UI only, no API routes
└── backend/    FastAPI + Supabase (Postgres/pgvector/Auth) + Groq
```

```
Browser ──(sign in/up)──────────────► Supabase Auth
   │
   └─ Bearer <access token> ─► FastAPI ─► Supabase Auth  ("who is this token?")
                                  ├────► Supabase Postgres (+ pgvector)
                                  └────► Groq (Llama 3.3 70B) via a LangGraph agent team
                                  └────► local sentence-transformers embeddings
```

## 1. Supabase

1. Create a project at [supabase.com](https://supabase.com).
2. SQL editor → run `backend/supabase/schema.sql` (tables, pgvector, RLS, `match_document_chunks`).
   *Already ran an earlier version of the schema?* Run `backend/supabase/migrations/001_tag_owner_and_version_privacy.sql` instead (safe to re-run).
3. Project Settings → API: copy the **Project URL**, **anon key** and **service_role key**. (No JWT secret needed.)
4. Authentication → Providers: make sure **Email** is enabled. For quick local testing you can turn off *Confirm email*; if it is on, the register page shows a "check your email" message instead of signing in straight away.

## 2. Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                   # Supabase URL + service_role key, Groq key
uvicorn main:app --reload --port 8000
```

Interactive API docs: http://localhost:8000/docs · health check: `/api/health`.
The first request that embeds text downloads the `all-MiniLM-L6-v2` model (~90 MB).

Tests (no live Supabase or Groq needed): `pip install -r requirements-dev.txt && pytest -v` → 83 tests.

## 3. Frontend

```bash
cd frontend
cp .env.example .env.local        # Supabase URL + anon key, NEXT_PUBLIC_API_URL=http://localhost:8000
npm install
npm run dev                       # http://localhost:3000
```

## What changed from the original Next.js app

| Before | Now |
|---|---|
| Next.js API routes (`app/api/*`) | FastAPI routers in `backend/app/routers` |
| Prisma + Neon Postgres | Supabase Postgres (`backend/supabase/schema.sql`) |
| NextAuth (credentials, bcrypt) | Supabase Auth; FastAPI asks Supabase Auth who the token belongs to |
| `middleware.ts` route protection | `useRequireAuth()` guard in client pages |
| Server components reading Prisma | Client pages calling `lib/api.ts` |
| Fuse.js fuzzy search | Hybrid pgvector semantic + title keyword search |
| pdf.js extraction in Node | `pypdf` in FastAPI |
| — | New `/chat` page for the RAG agent |

## Troubleshooting

- **401 "Invalid or expired token" on every request** — the backend validates each token by calling Supabase Auth (`auth.get_user`), so signing-key type doesn't matter. Check that `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` in `backend/.env` belong to the *same* project the frontend signs in to, and that the backend can reach `<SUPABASE_URL>/auth/v1`. Lookups are cached for 30 s (`AUTH_CACHE_TTL_SECONDS`).
- **Version history is sparse** — by design: auto-save collapses into one snapshot per `VERSION_MIN_INTERVAL_SECONDS` (default 600 s) of editing.
- **CORS errors** — add the frontend origin to `CORS_ORIGINS` in `backend/.env`.
- **Chat says nothing found** — documents are embedded when created/saved; anything created before the backend was running needs a re-save to be indexed.
