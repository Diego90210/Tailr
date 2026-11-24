-- DATA-04: generated CVs, usage metering and encrypted BYO keys (technical_requirements.md §5).

create table public.tailr_generated_cvs (
  id               uuid primary key default gen_random_uuid(),
  analysis_id      uuid not null references public.tailr_job_analyses(id) on delete cascade,
  docx_path        text,
  pdf_path         text,
  fill_pct         numeric(5,2),
  page_count       int,
  unverified_count int not null default 0,
  ui_locale        text not null check (ui_locale in ('es', 'en')),
  cv_lang          text not null check (cv_lang in ('es', 'en')),
  created_at       timestamptz not null default now()
);

create table public.tailr_usage_events (
  id          bigserial primary key,
  user_id     text,
  task        text not null,
  provider    text,
  model       text,
  tokens_in   int,
  tokens_out  int,
  cost_est    numeric(10,6),
  cost_source text not null default 'platform' check (cost_source in ('platform', 'byo_key')),
  latency_ms  int,
  created_at  timestamptz not null default now()
);

create table public.tailr_user_api_keys (
  id             uuid primary key default gen_random_uuid(),
  user_id        text not null unique,
  provider       text not null check (provider in ('groq', 'gemini', 'openrouter')),
  key_ciphertext bytea not null,
  key_hint       text not null,
  created_at     timestamptz not null default now(),
  last_used_at   timestamptz
);

create index tailr_generated_cvs_analysis_id_idx on public.tailr_generated_cvs (analysis_id);
create index tailr_usage_events_user_id_created_at_idx on public.tailr_usage_events (user_id, created_at);

alter table public.tailr_generated_cvs enable row level security;
alter table public.tailr_usage_events enable row level security;
alter table public.tailr_user_api_keys enable row level security;

revoke all on public.tailr_generated_cvs, public.tailr_usage_events, public.tailr_user_api_keys
  from public, anon, authenticated, service_role;
revoke all on sequence public.tailr_usage_events_id_seq
  from public, anon, authenticated, service_role;

grant select, insert, update, delete on public.tailr_generated_cvs to authenticated, service_role;

-- No client grants or policies: usage is server-insert only, and keys go through
-- the server's authenticated ownership check before it returns masked metadata.
grant insert on public.tailr_usage_events to service_role;
grant usage on sequence public.tailr_usage_events_id_seq to service_role;
grant select, insert, update, delete on public.tailr_user_api_keys to service_role;

create policy "own generated cvs" on public.tailr_generated_cvs
  for all to authenticated
  using (exists (
    select 1 from public.tailr_job_analyses a where a.id = tailr_generated_cvs.analysis_id
  ))
  with check (exists (
    select 1 from public.tailr_job_analyses a where a.id = tailr_generated_cvs.analysis_id
  ));
