-- DATA-03: job analyses and their follow-up records (technical_requirements.md §5.1).

create table public.tailr_job_analyses (
  id           uuid primary key default gen_random_uuid(),
  profile_id   uuid not null references public.tailr_profiles(id) on delete cascade,
  source_url   text,
  jd_text      text not null,
  jd_hash      text not null,
  jd_lang      text check (jd_lang in ('en', 'es', 'other')),
  company_name text,
  role_title   text,
  requirements jsonb not null,
  keywords     jsonb not null,
  match_score  numeric(5,2),
  red_flags    jsonb default '[]'::jsonb,
  created_at   timestamptz not null default now()
);

create table public.tailr_questions (
  id          uuid primary key default gen_random_uuid(),
  analysis_id uuid not null references public.tailr_job_analyses(id) on delete cascade,
  text        text not null,
  status      text not null default 'open' check (status in ('open', 'answered', 'skipped')),
  answer      text,
  fact_id     uuid references public.tailr_facts(id) on delete set null,
  created_at  timestamptz not null default now()
);

create table public.tailr_conversations (
  id          uuid primary key default gen_random_uuid(),
  analysis_id uuid not null references public.tailr_job_analyses(id) on delete cascade,
  messages    jsonb not null default '[]'::jsonb,
  confidence  numeric(5,4) not null default 0,
  updated_at  timestamptz not null default now()
);

create index tailr_job_analyses_profile_id_jd_hash_idx on public.tailr_job_analyses (profile_id, jd_hash);
create index tailr_questions_analysis_id_idx on public.tailr_questions (analysis_id);
create index tailr_questions_fact_id_idx on public.tailr_questions (fact_id);
create index tailr_conversations_analysis_id_idx on public.tailr_conversations (analysis_id);

alter table public.tailr_job_analyses enable row level security;
alter table public.tailr_questions enable row level security;
alter table public.tailr_conversations enable row level security;

revoke all on public.tailr_job_analyses, public.tailr_questions, public.tailr_conversations
  from public, anon, authenticated, service_role;
grant select, insert, update, delete
  on public.tailr_job_analyses, public.tailr_questions, public.tailr_conversations
  to authenticated, service_role;

create policy "own job analyses" on public.tailr_job_analyses
  for all to authenticated
  using (exists (
    select 1 from public.tailr_profiles p
    where p.id = tailr_job_analyses.profile_id and p.user_id = ((select auth.jwt()) ->> 'sub')
  ))
  with check (exists (
    select 1 from public.tailr_profiles p
    where p.id = tailr_job_analyses.profile_id and p.user_id = ((select auth.jwt()) ->> 'sub')
  ));

-- Child policies only see analyses allowed by the parent policy.
create policy "own questions" on public.tailr_questions
  for all to authenticated
  using (exists (
    select 1 from public.tailr_job_analyses a where a.id = tailr_questions.analysis_id
  ))
  with check (exists (
    select 1 from public.tailr_job_analyses a
    where a.id = tailr_questions.analysis_id
      and (tailr_questions.fact_id is null or exists (
        select 1 from public.tailr_facts f
        where f.id = tailr_questions.fact_id and f.profile_id = a.profile_id
      ))
  ));

create policy "own conversations" on public.tailr_conversations
  for all to authenticated
  using (exists (
    select 1 from public.tailr_job_analyses a where a.id = tailr_conversations.analysis_id
  ))
  with check (exists (
    select 1 from public.tailr_job_analyses a where a.id = tailr_conversations.analysis_id
  ));
