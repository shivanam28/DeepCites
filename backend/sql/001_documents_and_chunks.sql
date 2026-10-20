-- pgvector lives in the "extensions" schema on Supabase
create extension if not exists vector schema extensions;

-- ---------- documents ----------
create table public.documents (
  id           uuid primary key default gen_random_uuid(),
  user_id      uuid not null default auth.uid() references auth.users (id) on delete cascade,
  filename     text not null check (char_length(filename) between 1 and 255),
  storage_path text not null unique,
  mime_type    text not null,
  size_bytes   bigint not null check (size_bytes > 0 and size_bytes <= 10485760), -- 10 MB
  status       text not null default 'uploaded'
               check (status in ('uploaded', 'processing', 'ready', 'failed')),
  created_at   timestamptz not null default now(),
  -- the storage path must start with the owner's id, so file and row can't disagree
  check (storage_path like user_id::text || '/%'),
  unique (id, user_id)
);
create index documents_user_id_idx on public.documents (user_id);

-- ---------- document_chunks ----------
create table public.document_chunks (
  id          uuid primary key default gen_random_uuid(),
  document_id uuid not null,
  user_id     uuid not null default auth.uid(),
  chunk_index integer not null check (chunk_index >= 0),
  content     text not null check (char_length(content) between 1 and 4000),
  embedding   extensions.vector(384) not null,  -- BAAI/bge-small-en-v1.5 = 384 dimensions
  created_at  timestamptz not null default now(),
  unique (document_id, chunk_index),
  -- a chunk's owner must equal its document's owner
  foreign key (document_id, user_id)
    references public.documents (id, user_id) on delete cascade
);
create index document_chunks_user_id_idx on public.document_chunks (user_id);
-- No vector index yet, on purpose (see design decisions). Later, if needed:
-- create index on public.document_chunks using hnsw (embedding extensions.vector_cosine_ops);

-- ---------- Row Level Security ----------
alter table public.documents enable row level security;
alter table public.document_chunks enable row level security;

create policy documents_select on public.documents for select to authenticated
  using (user_id = (select auth.uid()));
create policy documents_insert on public.documents for insert to authenticated
  with check (user_id = (select auth.uid()));
create policy documents_update on public.documents for update to authenticated
  using (user_id = (select auth.uid())) with check (user_id = (select auth.uid()));
create policy documents_delete on public.documents for delete to authenticated
  using (user_id = (select auth.uid()));

create policy chunks_select on public.document_chunks for select to authenticated
  using (user_id = (select auth.uid()));
create policy chunks_insert on public.document_chunks for insert to authenticated
  with check (user_id = (select auth.uid()));
create policy chunks_delete on public.document_chunks for delete to authenticated
  using (user_id = (select auth.uid()));
-- chunks get no update policy: they are immutable (re-ingest = delete + insert)

-- ---------- explicit privileges ----------
revoke all on public.documents, public.document_chunks from anon;
grant select, insert, update, delete on public.documents to authenticated;
grant select, insert, delete on public.document_chunks to authenticated;

-- ---------- similarity search ----------
create or replace function public.match_document_chunks(
  query_embedding extensions.vector(384),
  match_count int default 5
)
returns table (id uuid, document_id uuid, chunk_index int, content text, similarity float)
language sql
stable
security invoker
set search_path = public, extensions
as $$
  select c.id, c.document_id, c.chunk_index, c.content,
         1 - (c.embedding <=> query_embedding) as similarity
  from public.document_chunks c
  where c.user_id = (select auth.uid())          -- belt and braces, on top of RLS
  order by c.embedding <=> query_embedding
  limit least(match_count, 20);                  -- hard cap on chunks returned
$$;

revoke execute on function public.match_document_chunks(extensions.vector, integer) from public, anon;
grant execute on function public.match_document_chunks(extensions.vector, integer) to authenticated;

notify pgrst, 'reload schema';  -- refresh the REST API's view of the database