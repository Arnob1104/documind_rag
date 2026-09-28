-- Migration for projects that already ran the ORIGINAL schema.sql.
-- (Fresh installs don't need this: schema.sql already contains it.)
-- Safe to run more than once.

-- 1. Tags get an owner, so delete can be restricted to the creator.
alter table public.tags
  add column if not exists created_by uuid references auth.users(id) on delete set null;

-- Backfill: attribute an existing tag to whoever attached it first.
-- Tags nobody ever used stay NULL and become undeletable through the API.
update public.tags t
set created_by = sub.user_id
from (
  select distinct on (tag_id) tag_id, user_id
  from public.document_tags
  order by tag_id
) sub
where t.id = sub.tag_id and t.created_by is null;

drop policy if exists "tags_write" on public.tags;
drop policy if exists "tags_insert" on public.tags;
drop policy if exists "tags_update" on public.tags;
drop policy if exists "tags_delete" on public.tags;
create policy "tags_insert" on public.tags
  for insert with check (auth.role() = 'authenticated' and created_by = auth.uid());
create policy "tags_update" on public.tags for update using (created_by = auth.uid());
create policy "tags_delete" on public.tags for delete using (created_by = auth.uid());

-- 2. Version history is owner-only, even for public documents.
drop policy if exists "versions_select" on public.document_versions;
create policy "versions_select" on public.document_versions
  for select using (
    exists (select 1 from public.documents d where d.id = document_id and d.author_id = auth.uid())
  );
