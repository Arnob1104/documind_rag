-- DocuMind Supabase schema
-- Run this in the Supabase SQL editor (or via `supabase db push`)

create extension if not exists vector;
create extension if not exists pgcrypto;

-- ─────────────────────────────────────────────────────────────
-- Documents
-- ─────────────────────────────────────────────────────────────
create table if not exists public.documents (
  id          uuid primary key default gen_random_uuid(),
  title       text not null,
  content     text not null default '',
  excerpt     text,
  is_public   boolean not null default false,
  author_id   uuid not null references auth.users(id) on delete cascade,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);

create table if not exists public.document_versions (
  id           uuid primary key default gen_random_uuid(),
  document_id  uuid not null references public.documents(id) on delete cascade,
  content      text not null,
  created_at   timestamptz not null default now()
);

create table if not exists public.tags (
  id          uuid primary key default gen_random_uuid(),
  name        text not null unique,
  color       text,
  created_by  uuid references auth.users(id) on delete set null
);

create table if not exists public.document_tags (
  document_id  uuid not null references public.documents(id) on delete cascade,
  tag_id       uuid not null references public.tags(id) on delete cascade,
  user_id      uuid not null references auth.users(id) on delete cascade,
  primary key (document_id, tag_id)
);

create table if not exists public.pdf_data (
  id             uuid primary key default gen_random_uuid(),
  document_id    uuid not null unique references public.documents(id) on delete cascade,
  filename       text not null,
  file_size      integer not null,
  extracted_text text not null,
  created_at     timestamptz not null default now(),
  updated_at     timestamptz not null default now()
);

-- ─────────────────────────────────────────────────────────────
-- RAG: chunked + embedded document content (384-dim = all-MiniLM-L6-v2)
-- ─────────────────────────────────────────────────────────────
create table if not exists public.document_chunks (
  id           uuid primary key default gen_random_uuid(),
  document_id  uuid not null references public.documents(id) on delete cascade,
  chunk_index  integer not null,
  content      text not null,
  embedding    vector(384),
  created_at   timestamptz not null default now()
);

create index if not exists document_chunks_embedding_idx
  on public.document_chunks using ivfflat (embedding vector_cosine_ops)
  with (lists = 100);

-- Agent chat history (optional but used by /chat)
create table if not exists public.chat_sessions (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null references auth.users(id) on delete cascade,
  title       text,
  created_at  timestamptz not null default now()
);

create table if not exists public.chat_messages (
  id           uuid primary key default gen_random_uuid(),
  session_id   uuid not null references public.chat_sessions(id) on delete cascade,
  role         text not null check (role in ('user','assistant','tool')),
  content      text not null,
  created_at   timestamptz not null default now()
);

-- ─────────────────────────────────────────────────────────────
-- Vector similarity search RPC (called from FastAPI via supabase-py)
-- Restricts to documents the caller may see: public OR owned by them.
-- ─────────────────────────────────────────────────────────────
create or replace function match_document_chunks (
  query_embedding vector(384),
  match_count int,
  requesting_user_id uuid
)
returns table (
  chunk_id uuid,
  document_id uuid,
  content text,
  similarity float,
  title text
)
language sql stable
as $$
  select
    c.id as chunk_id,
    c.document_id,
    c.content,
    1 - (c.embedding <=> query_embedding) as similarity,
    d.title
  from public.document_chunks c
  join public.documents d on d.id = c.document_id
  where d.is_public = true or d.author_id = requesting_user_id
  order by c.embedding <=> query_embedding
  limit match_count;
$$;

-- ─────────────────────────────────────────────────────────────
-- Row Level Security
-- ─────────────────────────────────────────────────────────────
alter table public.documents enable row level security;
alter table public.document_versions enable row level security;
alter table public.tags enable row level security;
alter table public.document_tags enable row level security;
alter table public.pdf_data enable row level security;
alter table public.document_chunks enable row level security;
alter table public.chat_sessions enable row level security;
alter table public.chat_messages enable row level security;

-- documents: read public or own; write only own
create policy "documents_select" on public.documents
  for select using (is_public = true or auth.uid() = author_id);
create policy "documents_insert" on public.documents
  for insert with check (auth.uid() = author_id);
create policy "documents_update" on public.documents
  for update using (auth.uid() = author_id);
create policy "documents_delete" on public.documents
  for delete using (auth.uid() = author_id);

-- versions/pdf_data/chunks follow the parent document's visibility
-- version history is owner-only (even for public documents)
create policy "versions_select" on public.document_versions
  for select using (
    exists (select 1 from public.documents d where d.id = document_id and d.author_id = auth.uid())
  );
create policy "versions_write" on public.document_versions
  for all using (
    exists (select 1 from public.documents d where d.id = document_id and d.author_id = auth.uid())
  );

create policy "pdf_select" on public.pdf_data
  for select using (
    exists (select 1 from public.documents d
            where d.id = document_id and (d.is_public or d.author_id = auth.uid()))
  );
create policy "pdf_write" on public.pdf_data
  for all using (
    exists (select 1 from public.documents d where d.id = document_id and d.author_id = auth.uid())
  );

create policy "chunks_select" on public.document_chunks
  for select using (
    exists (select 1 from public.documents d
            where d.id = document_id and (d.is_public or d.author_id = auth.uid()))
  );
create policy "chunks_write" on public.document_chunks
  for all using (
    exists (select 1 from public.documents d where d.id = document_id and d.author_id = auth.uid())
  );

-- tags: readable by everyone (authenticated); only the creator may change or delete
create policy "tags_select" on public.tags for select using (auth.role() = 'authenticated');
create policy "tags_insert" on public.tags
  for insert with check (auth.role() = 'authenticated' and created_by = auth.uid());
create policy "tags_update" on public.tags for update using (created_by = auth.uid());
create policy "tags_delete" on public.tags for delete using (created_by = auth.uid());

create policy "doc_tags_select" on public.document_tags
  for select using (
    exists (select 1 from public.documents d
            where d.id = document_id and (d.is_public or d.author_id = auth.uid()))
  );
create policy "doc_tags_write" on public.document_tags
  for all using (
    exists (select 1 from public.documents d where d.id = document_id and d.author_id = auth.uid())
  );

-- chat: only the owner
create policy "chat_sessions_owner" on public.chat_sessions
  for all using (auth.uid() = user_id);
create policy "chat_messages_owner" on public.chat_messages
  for all using (
    exists (select 1 from public.chat_sessions s where s.id = session_id and s.user_id = auth.uid())
  );

-- keep updated_at fresh
create or replace function public.set_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create trigger documents_set_updated_at
  before update on public.documents
  for each row execute function public.set_updated_at();

create trigger pdf_data_set_updated_at
  before update on public.pdf_data
  for each row execute function public.set_updated_at();
