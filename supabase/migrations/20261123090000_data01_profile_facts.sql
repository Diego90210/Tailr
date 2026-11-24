-- DATA-01: profile, facts and the CV sections that carry them (technical_requirements.md §5.1).
-- Tables are prefixed tailr_ because the Supabase project is shared (conventions.md).
-- format_specs / profiles.format_spec_id land in DATA-02: a forward reference here would need a
-- deferred constraint for no gain.

create table tailr_profiles (
  id          uuid primary key default gen_random_uuid(),
  user_id     text not null unique,                       -- Clerk sub
  name        text not null,
  contact     jsonb not null default '{}'::jsonb,         -- phone, email, linkedin, github, city
  languages   jsonb not null default '[]'::jsonb,         -- [{lang, level}]
  ui_locale   text not null default 'es',
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now(),
  constraint tailr_profiles_ui_locale_check check (ui_locale in ('en', 'es'))
);

create table tailr_facts (
  id          uuid primary key default gen_random_uuid(),
  profile_id  uuid not null references tailr_profiles(id) on delete cascade,
  kind        text not null,
  text        text not null,
  metrics     jsonb not null default '[]'::jsonb,
  provenance  text not null,
  verified_at timestamptz,
  created_at  timestamptz not null default now(),
  constraint tailr_facts_kind_check check (
    kind in ('experience', 'project', 'skill', 'education', 'certification', 'metric')
  ),
  constraint tailr_facts_provenance_check check (
    provenance in ('cv_upload', 'user_input', 'chat_answer')
  )
);

create table tailr_experience (
  id         uuid primary key default gen_random_uuid(),
  profile_id uuid not null references tailr_profiles(id) on delete cascade,
  company    text not null,
  role       text not null,
  start_date text,
  end_date   text,
  location   text,
  fact_ids   uuid[] not null default '{}'
);

create table tailr_projects (
  id         uuid primary key default gen_random_uuid(),
  profile_id uuid not null references tailr_profiles(id) on delete cascade,
  name       text not null,
  stack      text,
  url        text,
  fact_ids   uuid[] not null default '{}'
);

create table tailr_education (
  id          uuid primary key default gen_random_uuid(),
  profile_id  uuid not null references tailr_profiles(id) on delete cascade,
  degree      text not null,
  institution text not null,
  start_date  text,
  end_date    text,
  gpa         text
);

create table tailr_certifications (
  id         uuid primary key default gen_random_uuid(),
  profile_id uuid not null references tailr_profiles(id) on delete cascade,
  name       text not null,
  issuer     text
);

create index tailr_facts_profile_id_idx on tailr_facts (profile_id);
create index tailr_experience_profile_id_idx on tailr_experience (profile_id);
create index tailr_projects_profile_id_idx on tailr_projects (profile_id);
create index tailr_education_profile_id_idx on tailr_education (profile_id);
create index tailr_certifications_profile_id_idx on tailr_certifications (profile_id);

-- RLS ships with the table (AGENTS.md). DATA-05 extends the same pattern to the later tables.
alter table tailr_profiles enable row level security;
alter table tailr_facts enable row level security;
alter table tailr_experience enable row level security;
alter table tailr_projects enable row level security;
alter table tailr_education enable row level security;
alter table tailr_certifications enable row level security;

create policy "own profile" on tailr_profiles
  for all
  using (user_id = (auth.jwt() ->> 'sub'))
  with check (user_id = (auth.jwt() ->> 'sub'));

-- Derived tables inherit ownership through their parent profile.
create policy "own facts" on tailr_facts
  for all
  using (exists (
    select 1 from tailr_profiles p
    where p.id = tailr_facts.profile_id and p.user_id = (auth.jwt() ->> 'sub')
  ))
  with check (exists (
    select 1 from tailr_profiles p
    where p.id = tailr_facts.profile_id and p.user_id = (auth.jwt() ->> 'sub')
  ));

create policy "own experience" on tailr_experience
  for all
  using (exists (
    select 1 from tailr_profiles p
    where p.id = tailr_experience.profile_id and p.user_id = (auth.jwt() ->> 'sub')
  ))
  with check (exists (
    select 1 from tailr_profiles p
    where p.id = tailr_experience.profile_id and p.user_id = (auth.jwt() ->> 'sub')
  ));

create policy "own projects" on tailr_projects
  for all
  using (exists (
    select 1 from tailr_profiles p
    where p.id = tailr_projects.profile_id and p.user_id = (auth.jwt() ->> 'sub')
  ))
  with check (exists (
    select 1 from tailr_profiles p
    where p.id = tailr_projects.profile_id and p.user_id = (auth.jwt() ->> 'sub')
  ));

create policy "own education" on tailr_education
  for all
  using (exists (
    select 1 from tailr_profiles p
    where p.id = tailr_education.profile_id and p.user_id = (auth.jwt() ->> 'sub')
  ))
  with check (exists (
    select 1 from tailr_profiles p
    where p.id = tailr_education.profile_id and p.user_id = (auth.jwt() ->> 'sub')
  ));

create policy "own certifications" on tailr_certifications
  for all
  using (exists (
    select 1 from tailr_profiles p
    where p.id = tailr_certifications.profile_id and p.user_id = (auth.jwt() ->> 'sub')
  ))
  with check (exists (
    select 1 from tailr_profiles p
    where p.id = tailr_certifications.profile_id and p.user_id = (auth.jwt() ->> 'sub')
  ));
