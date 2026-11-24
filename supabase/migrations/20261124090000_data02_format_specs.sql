-- DATA-02: format specs and the global default (technical_requirements.md §5.1, §11.1).
-- The seed mirrors services/docgen/format_specs.py DEFAULT_FORMAT_SPEC; keep both in step.

create table tailr_format_specs (
  id         uuid primary key default gen_random_uuid(),
  owner_id   text,                          -- null = global default
  name       text not null default 'default',
  spec       jsonb not null,
  is_default boolean not null default false,
  created_at timestamptz not null default now()
);

-- null means "use the global default".
alter table tailr_profiles
  add column format_spec_id uuid references tailr_format_specs(id);

insert into tailr_format_specs (owner_id, name, spec, is_default) values (
  null,
  'default',
  $json$
  {
    "font": "Cambria",
    "nameSizePt": 15,
    "nameBold": true,
    "bodySizePt": 11,
    "dateItalic": true,
    "linkColor": "0563C1",
    "linkUnderline": true,
    "marginsIn": { "top": 0.3, "bottom": 0.3, "left": 0.5, "right": 0.5 },
    "lineSpacing": 1.13,
    "headingSpaceBeforePt": 8,
    "itemSpaceBeforePt": 3,
    "pageSizeIn": { "w": 8.5, "h": 11.0 },
    "sectionOrder": ["summary", "experience", "projects", "education", "certifications", "skills", "languages"],
    "headings": {
      "en": { "summary": "PROFESSIONAL PROFILE", "experience": "EXPERIENCE", "projects": "PROJECTS",
              "education": "EDUCATION", "certifications": "CERTIFICATIONS", "skills": "SKILLS",
              "languages": "LANGUAGES" },
      "es": { "summary": "PERFIL PROFESIONAL", "experience": "EXPERIENCIA", "projects": "PROYECTOS",
              "education": "EDUCACIÓN", "certifications": "CERTIFICACIONES", "skills": "HABILIDADES",
              "languages": "IDIOMAS" }
    },
    "rightAlignedDates": true,
    "tabStopIn": 7.5
  }
  $json$::jsonb,
  true
);

alter table tailr_format_specs enable row level security;

-- Global rows are readable by everyone and writable by no one through the API (§5.2).
create policy "read global specs" on tailr_format_specs
  for select
  using (owner_id is null);

create policy "own specs" on tailr_format_specs
  for all
  using (owner_id = (auth.jwt() ->> 'sub'))
  with check (owner_id = (auth.jwt() ->> 'sub'));
