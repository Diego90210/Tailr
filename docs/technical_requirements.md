# Technical Requirements — Tailr

| Field | Value |
|---|---|
| Version | 0.1 (draft) |
| Companion document | `PRD.md` |
| License | MIT |
| Target deployment | Vercel (free tier), with Supabase, Clerk and Upstash free tiers |
| Primary market | Spanish-speaking users |
| UI languages | Spanish (default) and English |

---

## 1. Purpose and scope

This document is the technical counterpart of `PRD.md`. It specifies how Tailr is built: architecture, data model, contracts, algorithms, security controls and deployment. Every functional requirement (`RF-*`) referenced here is defined in the PRD.

Guiding principle: **the language model is a replaceable component; the structure around it is the product.** Anything that can be deterministic (formatting, pagination, fact validation, scoring) must be code, not a prompt.

---

## 2. Architecture overview

```
┌──────────────────────────── Browser (Next.js App Router) ─────────────────────────────┐
│  • Clerk session (middleware-protected routes)                                          │
│  • Client-side CV extraction: pdf.js (PDF), mammoth.js (DOCX)                           │
│  • Profile form · clarification chat (streaming) · preview · download                   │
└───────────────┬──────────────────────────────────────────────────────┬─────────────────┘
                │ Server Actions / route handlers (zod-validated)      │
┌───────────────▼──────────────────────────────────────────────────────▼─────────────────┐
│                          Next.js on Vercel — application core                          │
│  • Pipeline orchestrator (state machine)                                               │
│  • LLM layer: adapters, task router, cascade fallback, cost meter                      │
│  • Fact-locking validator · confidence scorer                                          │
│  • Rate limiting (Upstash) · quotas · feature flags                                    │
│  • i18n via next-intl                                                                  │
└──────┬──────────────────┬──────────────────┬───────────────────┬───────────────────────┘
       │                  │                  │                   │
┌──────▼───────┐  ┌───────▼────────┐  ┌──────▼─────────┐  ┌──────▼────────────────────┐
│ Supabase     │  │ LLM providers  │  │ Upstash Redis  │  │ Python service (Vercel)   │
│ Postgres+RLS │  │ Groq / Gemini  │  │ rate limit +   │  │ python-docx + paginator   │
│ Storage      │  │ / OpenRouter…  │  │ cache + queues │  │ (deterministic, 1 page)   │
└──────────────┘  └────────────────┘  └────────────────┘  └───────────────────────────┘
```

**Hard boundary:** the Python service holds no business logic beyond document rendering and pagination. It receives a fully validated, fact-locked content tree and a `format_spec`.

---

## 3. Technology stack

| Layer | Choice | Notes |
|---|---|---|
| Framework | Next.js (App Router) + TypeScript | Deployed on Vercel |
| Styling | Tailwind CSS + shadcn/ui | Accessible primitives |
| Auth | Clerk | Middleware-protected routes |
| Database | Supabase Postgres | RLS on every table |
| Object storage | Supabase Storage | Generated `.docx` / `.pdf` only |
| Cache / rate limit | Upstash Redis + `@upstash/ratelimit` | Free tier |
| Validation | zod | Boundary + LLM output validation |
| i18n | next-intl | `[locale]` segment, `es` default |
| LLM access | Provider adapters behind one interface | No SDK leakage |
| Doc generation | Python 3.11 + python-docx | Pure Python, serverless-friendly |
| Measurement | Pillow (`ImageFont.getlength`) + Cambria font file | For pagination |
| Client extraction | pdf.js, mammoth.js | Keeps heavy parsing off the server |
| Testing | Vitest (unit), Playwright (e2e) | — |
| CI/CD | GitHub Actions + Vercel Git integration | — |

> Pin exact versions in `package.json` / `requirements.txt`. Do not use floating major versions in production.

---

## 4. Repository structure

```
tailr/
├── apps/
│   └── web/                        # Next.js application
│       ├── app/
│       │   ├── [locale]/
│       │   │   ├── (marketing)/
│       │   │   ├── dashboard/
│       │   │   ├── profile/
│       │   │   ├── tailor/         # posting + chat + generate
│       │   │   └── history/
│       │   └── api/
│       │       ├── profile/route.ts
│       │       ├── profile/parse/route.ts
│       │       ├── analyze/route.ts
│       │       ├── chat/route.ts
│       │       ├── generate/route.ts
│       │       └── cv/[id]/route.ts
│       ├── components/
│       ├── lib/
│       │   ├── llm/                # adapter layer (no SDK usage outside here)
│       │   │   ├── index.ts
│       │   │   ├── router.ts
│       │   │   ├── types.ts
│       │   │   ├── cost.ts
│       │   │   └── providers/
│       │   │       ├── groq.ts
│       │   │       ├── gemini.ts
│       │   │       └── openrouter.ts
│       │   ├── pipeline/           # orchestrator + state machine
│       │   ├── facts/              # fact-locking + validation
│       │   ├── scoring/            # confidence + match score
│       │   ├── ratelimit/
│       │   ├── supabase/
│       │   └── prompts/            # thin loader over /prompts
│       ├── messages/
│       │   ├── es.json
│       │   └── en.json
│       └── tests/
├── services/
│   └── docgen/                     # Python: docx + pagination + preview
│       ├── api/
│       │   ├── __init__.py
│       │   └── health.py           # Vercel entrypoint: health + POST /docgen
│       ├── endpoint.py             # shared-secret auth, GenerateRequest, response
│       ├── builder.py
│       ├── measure.py
│       ├── converge.py
│       ├── preview.py              # HTML replica + headless-Chromium PNG
│       ├── format_specs.py
│       └── requirements.txt
├── prompts/                        # versioned Markdown skills
│   ├── analyze-jd.md
│   ├── extract-profile.md
│   ├── gap-questions.md
│   ├── rewrite-bullets.md
│   ├── diagnose-ats.md
│   └── humanizer.md
├── supabase/
│   └── migrations/
├── docs/
│   ├── PRD.md
│   └── technical_requirements.md
├── LICENSE
└── CONTRIBUTING.md
```

---

## 5. Data model

### 5.1 DDL (Postgres / Supabase)

```sql
-- Identity is provided by Clerk; its JWT `sub` is the user key.
create table profiles (
  id              uuid primary key default gen_random_uuid(),
  user_id         text not null,                       -- Clerk sub
  name            text not null,
  contact         jsonb not null default '{}'::jsonb,  -- phone, email, linkedin, github, city?
  languages       jsonb not null default '[]'::jsonb,  -- [{lang, level}]
  format_spec_id  uuid references format_specs(id),
  ui_locale       text not null default 'es',          -- en | es
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);

create table facts (
  id           uuid primary key default gen_random_uuid(),
  profile_id   uuid not null references profiles(id) on delete cascade,
  kind         text not null,      -- experience | project | skill | education | certification | metric
  text         text not null,
  metrics      jsonb default '[]'::jsonb,
  provenance   text not null,      -- cv_upload | user_input | chat_answer
  verified_at  timestamptz,
  created_at   timestamptz not null default now()
);

create table experience (
  id          uuid primary key default gen_random_uuid(),
  profile_id  uuid not null references profiles(id) on delete cascade,
  company     text not null,
  role        text not null,
  start_date  text,
  end_date    text,
  location    text,
  fact_ids    uuid[] not null default '{}'
);

create table projects (
  id          uuid primary key default gen_random_uuid(),
  profile_id  uuid not null references profiles(id) on delete cascade,
  name        text not null,
  stack       text,
  url         text,
  fact_ids    uuid[] not null default '{}'
);

create table education (
  id          uuid primary key default gen_random_uuid(),
  profile_id  uuid not null references profiles(id) on delete cascade,
  degree      text not null,
  institution text not null,
  start_date  text,
  end_date    text,
  gpa         text
);

create table certifications (
  id          uuid primary key default gen_random_uuid(),
  profile_id  uuid not null references profiles(id) on delete cascade,
  name        text not null,
  issuer      text
);

create table format_specs (
  id           uuid primary key default gen_random_uuid(),
  owner_id     text,                        -- null = global default
  name         text not null default 'default',
  spec         jsonb not null,              -- see §11.1
  is_default   boolean not null default false,
  created_at   timestamptz not null default now()
);

create table job_analyses (
  id               uuid primary key default gen_random_uuid(),
  profile_id       uuid not null references profiles(id) on delete cascade,
  source_url       text,
  jd_text          text not null,
  jd_hash          text not null,           -- for caching
  jd_lang          text,                    -- en | es | other
  company_name     text,
  role_title       text,
  requirements     jsonb not null,          -- [{text, type: must|nice, category}]
  keywords         jsonb not null,          -- [{term, kind, present_in_profile}]
  match_score      numeric(5,2),
  red_flags        jsonb default '[]'::jsonb,
  created_at       timestamptz not null default now()
);
create index on job_analyses (profile_id, jd_hash);

create table questions (
  id           uuid primary key default gen_random_uuid(),
  analysis_id  uuid not null references job_analyses(id) on delete cascade,
  text         text not null,
  status       text not null default 'open',   -- open | answered | skipped
  answer       text,
  fact_id      uuid references facts(id),
  created_at   timestamptz not null default now()
);

create table conversations (
  id           uuid primary key default gen_random_uuid(),
  analysis_id  uuid not null references job_analyses(id) on delete cascade,
  messages     jsonb not null default '[]'::jsonb,
  confidence   numeric(5,4) not null default 0,
  updated_at   timestamptz not null default now()
);

create table generated_cvs (
  id                uuid primary key default gen_random_uuid(),
  analysis_id       uuid not null references job_analyses(id) on delete cascade,
  docx_path         text,
  pdf_path          text,
  fill_pct          numeric(5,2),
  page_count        int,
  unverified_count  int not null default 0,
  ui_locale         text not null,
  cv_lang           text not null,
  created_at        timestamptz not null default now()
);

create table usage_events (
  id          bigserial primary key,
  user_id     text,
  task        text not null,
  provider    text,
  model       text,
  tokens_in   int,
  tokens_out  int,
  cost_est    numeric(10,6),
  cost_source text not null default 'platform',  -- platform | byo_key
  latency_ms  int,
  created_at  timestamptz not null default now()
);
create index on usage_events (user_id, created_at);

-- BYO-key (RF-15.22–RF-15.27). v1 stores one key per user.
create table user_api_keys (
  id             uuid primary key default gen_random_uuid(),
  user_id        text not null unique,       -- Clerk sub
  provider       text not null,              -- groq | gemini | openrouter
  key_ciphertext bytea not null,             -- AES-256-GCM; never logged, never returned
  key_hint       text not null,              -- e.g. 'gsk_…4f2a' for masked display only
  created_at     timestamptz not null default now(),
  last_used_at   timestamptz
);
```

### 5.2 Row Level Security

```sql
alter table profiles enable row level security;

create policy "own profile" on profiles
  for all using (user_id = (auth.jwt() ->> 'sub'))
  with check (user_id = (auth.jwt() ->> 'sub'));

-- Derived tables inherit ownership through their parent.
alter table facts enable row level security;

create policy "own facts" on facts
  for all using (
    exists (select 1 from profiles p
            where p.id = facts.profile_id
              and p.user_id = (auth.jwt() ->> 'sub'))
  );
-- Repeat the pattern for experience, projects, education, certifications,
-- job_analyses, questions, conversations, generated_cvs.
```

- `usage_events` is **insert-only from the server** (service role); never exposed to clients.
- `user_api_keys` is **never readable through the API**: the client only ever receives `provider` and `key_hint`, never `key_ciphertext`. Encryption and decryption happen exclusively in the service role.
- `format_specs` rows with `owner_id is null` are readable by everyone, writable by no one through the API.

---

## 6. Contracts (TypeScript + zod)

```ts
// lib/contracts/profile.ts
import { z } from 'zod';

export const FactSchema = z.object({
  id: z.string().uuid(),
  kind: z.enum(['experience','project','skill','education','certification','metric']),
  text: z.string().min(1).max(500),
  metrics: z.array(z.string()).default([]),
  provenance: z.enum(['cv_upload','user_input','chat_answer']),
});

export const ExperienceSchema = z.object({
  company: z.string().min(1),
  role: z.string().min(1),
  startDate: z.string().nullable(),
  endDate: z.string().nullable(),      // null = present
  bullets: z.array(z.string()),
});

export const ProfileSchema = z.object({
  name: z.string().min(1),
  contact: z.object({
    phone: z.string().optional(),
    email: z.string().email(),
    linkedin: z.string().url().optional(),
    github: z.string().url().optional(),
    city: z.string().optional(),       // optional: PRD requires it NOT to be shown by default
  }),
  languages: z.array(z.object({ lang: z.string(), level: z.string() })),
  experience: z.array(ExperienceSchema),
  projects: z.array(z.object({
    name: z.string(), stack: z.string().optional(),
    url: z.string().url().optional(), bullets: z.array(z.string()),
  })),
  skills: z.array(z.string()),
  education: z.array(z.object({ degree: z.string(), institution: z.string() })),
  certifications: z.array(z.string()),
});

// lib/contracts/analysis.ts
export const RequirementSchema = z.object({
  text: z.string(),
  type: z.enum(['must','nice']),
  category: z.enum(['technical','soft','tool','domain','logistics']),
});

export const AnalysisSchema = z.object({
  jdLang: z.enum(['en','es','other']),
  companyName: z.string().nullable(),
  roleTitle: z.string().nullable(),
  requirements: z.array(RequirementSchema),
  keywords: z.array(z.object({
    term: z.string(),
    kind: z.enum(['technical','soft','tool','domain']),
    presentInProfile: z.boolean(),
  })),
  matchScore: z.number().min(0).max(100),
  redFlags: z.array(z.string()),
});

// lib/contracts/generation.ts — what the Python service receives
export const GenerateRequestSchema = z.object({
  formatSpec: z.record(z.any()),
  locale: z.enum(['en','es']).optional(),
  content: z.object({
    header: z.object({ name: z.string(), contactLine: z.string() }),
    summary: z.string(),
    experience: z.array(z.object({
      company: z.string(), role: z.string(),
      start: z.string(), end: z.string(),
      bullets: z.array(z.object({
        text: z.string(),
        factIds: z.array(z.string()).min(1),   // fact-locking enforced at the edge
      })),
    })),
    projects: z.array(z.object({
      name: z.string(), stack: z.string().optional(), url: z.string().url().optional(),
      bullets: z.array(z.object({ text: z.string(), factIds: z.array(z.string()).min(1) })),
    })),
    education: z.array(z.string()),
    certifications: z.array(z.string()),
    skills: z.array(z.string()),
    languages: z.array(z.string()),
  }),
});
```

A `GenerateRequest` that fails validation is rejected with `400`; no document is produced.

---

## 7. LLM abstraction layer

### 7.1 Interface

```ts
// lib/llm/types.ts
export type TaskKind =
  | 'extract_profile'
  | 'analyze_jd'
  | 'gap_questions'
  | 'rewrite_bullets'
  | 'classify_facts';

export interface LLMRequest<T> {
  task: TaskKind;
  system: string;
  messages: { role: 'user' | 'assistant'; content: string }[];
  schema?: z.ZodType<T>;
  maxTokens: number;
  temperature: number;
  locale: 'en' | 'es';
}

export interface LLMProvider {
  readonly name: string;
  complete<T>(req: LLMRequest<T>): Promise<{
    data: T;
    usage: { tokensIn: number; tokensOut: number };
    model: string;
  }>;
}
```

### 7.2 Task routing

| Task | Default model class | Rationale |
|---|---|---|
| `extract_profile` | Cheap/fast | Structured extraction, not writing |
| `analyze_jd` | Cheap/fast | Classification + extraction |
| `classify_facts` | Cheap/fast | Coverage classification |
| `gap_questions` | Mid | Wording quality matters |
| `rewrite_bullets` | Best available | This is where quality shows |

Routing is defined in environment variables, not in code. Only ZDR-approved providers may
appear here (§8.1): Groq is the primary, and the Gemini free tier is excluded because it
trains on unpaid-service content.

```env
LLM_ROUTE_EXTRACT_PROFILE=groq:openai/gpt-oss-120b
LLM_ROUTE_ANALYZE_JD=groq:openai/gpt-oss-120b
LLM_ROUTE_GAP_QUESTIONS=groq:openai/gpt-oss-120b
LLM_ROUTE_REWRITE_BULLETS=groq:openai/gpt-oss-120b
LLM_ROUTE_CLASSIFY_FACTS=groq:openai/gpt-oss-120b
LLM_FALLBACK_CHAIN=groq
```

### 7.3 Cascade fallback

```
for provider in [primary, ...fallback_chain]:
    try:
        result = provider.complete(req)
        if result fails schema validation: continue   # try next provider
        record usage; return result
    except (RateLimit, Timeout, UpstreamError):
        record failure; continue
raise AllProvidersFailed
```

### 7.4 Requirements
- **TR-LLM-1** No provider SDK may be imported outside `lib/llm/providers/**`.
- **TR-LLM-2** Every LLM response is validated with zod before use; invalid output never reaches the user or the database.
- **TR-LLM-3** Every call writes a `usage_events` row (provider, model, tokens, estimated cost, latency).
- **TR-LLM-4** Prompts are loaded from `prompts/*.md` at build time; a missing prompt is a startup error.
- **TR-LLM-5** Swapping or adding a provider must require only a new adapter file plus routing env vars.

---

## 8. Pipeline orchestration

### 8.1 State machine

```
IDLE
 └─(posting submitted)→ ANALYZING
       └─→ ANALYZED
             └─(gaps detected)→ AWAITING_ANSWERS ⇄ (chat rounds)
                   ├─(confidence ≥ 0.95)→ READY
                   └─(user forces)→ READY_FORCED
                         └─→ GENERATING
                               ├─(validation fails)→ REGENERATING (max 2 retries)
                               └─(ok)→ DONE
```

### 8.2 Steps

| # | Step | Deterministic? | Notes |
|---|---|---|---|
| 1 | Normalize posting text | Yes | strip boilerplate, cap length |
| 2 | Hash + cache lookup | Yes | reuse analysis for identical postings |
| 3 | Analyze posting (LLM) | No | structured output, zod-validated |
| 4 | Retrieval of relevant facts | Yes | keyword/embedding match, not full profile |
| 5 | Classify coverage (LLM) | No | COVERED / PARTIAL / UNKNOWN per requirement |
| 6 | Confidence score | **Yes** | §10 |
| 7 | If < threshold: generate questions (LLM) | No | max 4 per round, in user's locale |
| 8 | Persist answers as facts | Yes | provenance = `chat_answer` |
| 9 | Select sections and order | Yes + LLM assist | relevance ranking |
| 10 | Rewrite bullets (LLM) | No | XYZ formula, fact IDs required |
| 11 | Fact-locking validation | **Yes** | §9 |
| 12 | Humanizer pass (LLM) | No | then re-validate numbers again |
| 13 | Build content tree | Yes | |
| 14 | Render + paginate (Python) | **Yes** | §11 |
| 15 | Persist + expose download | Yes | |

Steps 1, 2, 4, 6, 8, 9, 11, 13, 14, 15 are pure code. They are the backbone that survives any model change.

---

## 9. Fact-locking engine

The core guarantee of the product.

### 9.1 Generation contract

The LLM receives facts as an explicitly numbered list and must return bullets that reference them:

```json
{
  "bullets": [
    { "text": "Shipped 5 web applications in 2-week cycles with Next.js and Supabase.",
      "factIds": ["f_8a1c", "f_91bd"], "section": "experience" }
  ]
}
```

### 9.2 Validation algorithm

```
validateBullet(bullet, factsById):
  1. reject if bullet.factIds is empty
  2. reject if any factId is unknown to the profile
  3. numbers := regex(bullet.text, /\d+(?:[.,]\d+)?%?/g)
     for each number:
        allowed := numbers appearing in the referenced facts' text or metrics
        reject if number ∉ allowed
  4. reject if bullet.text length > 220 chars
  5. accept
```

- A rejected bullet is **dropped**, never "fixed" silently.
- Each rejection is logged with the reason, to measure the hallucination rate over time.
- After the humanizer pass, step 3 runs **again** (rewriting can introduce numbers).

### 9.3 Suggested facts

If the LLM proposes a fact not present in the profile, it goes to a `suggested_facts` queue surfaced to the user as a question ("You mentioned X, is that accurate?"). It is never written into the CV without confirmation.

---

## 10. Confidence scoring

```
weight(req)  = req.type === 'must' ? 0.7 : 0.3
status(req)  ∈ { COVERED: 1.0, PARTIAL: 0.5, UNKNOWN: 0.0 }

confidence = Σ (weight_i × status_i) / Σ (weight_i)
```

Rules:
- `UNKNOWN` on a `must` requirement is always a blocking gap.
- A `logistics` requirement the user cannot satisfy (e.g., on-site city) raises a blocking warning regardless of score.
- The threshold (default `0.95`) is configurable via `CONFIDENCE_THRESHOLD`.
- Forcing generation records `confidence_at_generation` and `forced = true` for later analysis.

---

## 11. Format and pagination engine (Python service)

### 11.1 `format_spec` schema

```json
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
  "sectionOrder": ["summary","experience","projects","education","certifications","skills","languages"],
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
```

### 11.2 Algorithm

```
1. build_docx(content, format_spec)
2. measure(docx):
     for each paragraph:
        lines = greedy_word_wrap(text, usable_width, font_metrics)
        height = space_before + space_after + lines × line_height(font, size, spacing)
     fill = CALIBRATION × Σ height / usable_height   (CALIBRATION = 0.93, see below)
3. if page_count > 1 or fill > 0.98:
     request compression of lowest-priority bullets (caller decides priority)
     goto 1     (max 3 iterations)
4. if fill < 0.90 and spare facts exist:
     allow enriching bullets
     goto 1     (max 2 iterations)
5. return { docx, content, fill_pct, line_count, page_count, missing_fonts, iterations, warning }
   (`warning = "over_one_page"` when the best attempt still exceeds one page; TR-FMT-1)
```

`converge()` receives `compress` / `enrich` callbacks from the caller — which bullets are expendable or spare is business logic, so docgen never decides it. A callback returns a new content tree, or `None` when nothing is left to cut or add.

`CALIBRATION` (0.93) is a fixed factor derived from the SPIKE-01 Word oracle: the raw line-box sum over-counts `space_before`/heading gaps ~6–8%, so without it `fill_pct` would exceed true occupancy and the 0.90/0.98 thresholds (RF-14.2) would underfill the page. Re-derive it only if the spec or the oracle corpus changes.

### 11.3 Requirements
- **TR-FMT-1** Output must be exactly 1 page; if the loop cannot converge, return the best attempt plus a `page_count > 1` warning rather than failing silently.
- **TR-FMT-2** Text measurement uses real font metrics (`Pillow` + the actual font file), never estimated character counts.
- **TR-FMT-3** Known divergence: Word and LibreOffice paginate differently. The measurement is authoritative; PDF rendering is a secondary check.
- **TR-FMT-4** The engine is fully deterministic: same input tree + same spec ⇒ byte-identical output.
- **TR-FMT-5** Missing fonts must be reported in the response (`missing_fonts`), not substituted silently.

---

## 12. Document generation service (Python)

| Item | Detail |
|---|---|
| Runtime | Python 3.11 on Vercel serverless functions (see the renderer note below) |
| Endpoint | `POST /docgen` (private, server-to-server only) |
| Auth | `Authorization: Bearer <DOCGEN_SHARED_SECRET>`, plus Vercel deployment protection |
| Libraries | `python-docx`, `Pillow`, plus a document renderer for the preview image (see §12.1) |
| Input | `GenerateRequest` (§6) |
| Output | `{ docx_b64, preview_png_b64, fill_pct, line_count, page_count, missing_fonts[], iterations, warning }` (`warning = "over_one_page"` possible, §11.2) |
| Timeout budget | < 10 s p95 for the `.docx`; < 15 s p95 including the preview render |
| Size | Keep the bundle small; the renderer is the only heavy dependency |

`services/docgen/endpoint.py` owns the boundary: bearer-secret check, `GenerateRequest` validation (a malformed tree is a `400`, never a builder `500`), `converge()` and one preview render. An unset `DOCGEN_SHARED_SECRET` fails closed with `503 DOCGEN_NOT_CONFIGURED`; a bad token is `401`. Errors use the §13 envelope. If `CHROME_BIN`/the browser is unavailable the endpoint returns `503 PREVIEW_UNAVAILABLE` instead of a silent blank image — the `.docx` renders, but the P7 preview is part of the contract, so this is a deployment failure the caller must see.

Vercel routes every request to the single Python entrypoint (`api/health.py`, SETUP-06), which dispatches `GET` health and `POST /docgen` on `self.path`; the endpoint is not exposed through the Next.js app's public `/api` surface.

### 12.1 Preview image rendering (decision 6)

The preview on P7 is an **image rendered by this service**, so the user sees exactly what they are about to download. That guarantee has a real cost:

- Rendering a `.docx` to an image needs a document renderer. LibreOffice **does not fit** in a Vercel serverless bundle; a headless Chromium rendering a faithful HTML replica does, at roughly 50 MB.
- **Consequence:** docgen is the single component most likely to outgrow the free Vercel tier.

Options, in order of preference:

| Option | Trade-off |
|---|---|
| **A. HTML replica rendered by headless Chromium** inside the Vercel function | Stays free and self-contained. The replica must be kept in sync with the python-docx builder, enforced by a shared fidelity test |
| **B. Separate docgen host** running a container with LibreOffice, on a free tier | Highest fidelity. Adds a second deploy target, cold starts and ops surface |
| **C. Defer the image** and ship a client-side preview for MVP | Cheapest. Breaks the byte-faithful guarantee until A or B lands |

**Recommendation:** start with **A**, and add a fidelity test that renders the same content tree both ways and compares page count, line breaks and `fill_pct`. Keep the `/docgen` contract fixed (`preview_png_b64`) so moving to **B** later is a hosting decision, not a rewrite.

**SPIKE-01 verdict (2026-10-07): A confirmed.** On a 5-fixture corpus with Word as oracle: A matched `page_count` and `line_count` 5/5 (mean line-break match 0.967, `fill_pct` delta ≤ 0.04); the LibreOffice container substituted NotoSerif for Cambria and diverged 2/5 on line count (mean match 0.843, fill delta up to 0.12). Details: `SPIKE-01.md`, raw data `services/docgen/spike_output/report.md`.

Implemented in `services/docgen/preview.py`: `build_html(content, spec, locale)` is the one replica shared with the spike, and `render_png` / `preview_png_b64` screenshot page 1 with a Chromium-family binary (`CHROME_BIN`, else a local Edge/Chrome/Chromium) at the spec's page size ×96 dpi. The binary is the deployment dependency; the module raises `PreviewRenderError` instead of returning a blank image.

PDF export is **deferred** (PRD §21.1, decision 2). If it is added later it must not run inside the request path.

---

## 13. API specification

### Conventions
- JSON only. All bodies zod-validated.
- Errors: `{ "error": { "code": "RATE_LIMITED", "message": "...", "details": {} } }`
- Localized `message` based on `Accept-Language` / user locale.

| Code | Meaning |
|---|---|
| 400 | Validation error |
| 401 | Unauthenticated |
| 403 | Not the owner of the resource |
| 409 | State conflict (e.g., generating before answering) |
| 413 | Payload too large |
| 422 | LLM output failed schema validation |
| 429 | Rate limited (`Retry-After` header) |
| 502 | All LLM providers failed |
| 503 | Global budget exhausted (degraded mode) |

### `POST /api/profile/parse`
```json
// request
{ "cvText": "…", "locale": "es" }
// response 200
{
  "profile": { /* partial ProfileSchema */ },
  "fieldConfidence": { "experience.0.startDate": 0.42, "projects": 0.31 },
  "undetected": ["projects", "certifications", "experience.0.startDate"]
}
```

### `POST /api/analyze`
```json
// request
{ "profileId": "…", "jdText": "…", "sourceUrl": null }
// response 200
{
  "analysisId": "…",
  "jdLang": "es",
  "matchScore": 87.5,
  "requirements": [ { "text": "Node.js", "type": "must", "category": "technical" } ],
  "keywords": [ { "term": "Node.js", "kind": "technical", "presentInProfile": true } ],
  "confidence": 0.78,
  "blocking": true
}
```

### `POST /api/chat`
```json
// request
{ "analysisId": "…", "message": "I used MongoDB on a university project" }
// response 200 (streamed)
{ "reply": "…", "newFacts": ["…"], "confidence": 0.93, "remainingGaps": 2 }
```

### `POST /api/generate`
```json
// request
{ "analysisId": "…", "force": false, "includePdf": false }
// response 200
{
  "cvId": "…",
  "docxUrl": "…",
  "previewUrl": "…",
  "fillPct": 96.8,
  "pageCount": 1,
  "unverifiedCount": 0,
  "cvLang": "es"
}
```

---

## 14. Authentication and authorization

- Clerk handles sign-up, sign-in, sessions and OAuth.
- The Clerk session JWT is forwarded to Supabase; Supabase is configured with Clerk as a third-party auth provider.
- RLS policies read the user key from `auth.jwt() ->> 'sub'`.
- Server code never trusts a `user_id` sent by the client; it always resolves it from the session.
- Public routes: landing, docs, `/api/cv/[id]` behind a signed, short-lived URL (not a plain public path).
- Guest mode: a **signed, HttpOnly `guest_session` cookie** with an IP-derived quota. No Clerk anonymous accounts (decision 1). On first sign-in the guest's profile answers and generated CV are migrated into the new account.

---

## 15. Security requirements

| ID | Requirement |
|---|---|
| TR-SEC-1 | The job posting and CV text are **untrusted data**. They are wrapped in explicit delimiters and the system prompt states that content inside them is never an instruction. |
| TR-SEC-2 | Heuristic injection detection (e.g. "ignore previous instructions", role reassignment) logs and neutralizes attempts. |
| TR-SEC-3 | No secret ever reaches the client bundle; provider keys live only in server-side env vars. |
| TR-SEC-4 | Uploaded files are validated by MIME type, extension and size (max 5 MB) before processing. |
| TR-SEC-5 | The original CV binary is never persisted; only extracted text and the resulting profile. |
| TR-SEC-6 | RLS on every table; a server-side ownership check on every mutation, in addition to RLS. |
| TR-SEC-7 | Logs and telemetry exclude CV, posting and chat content; only IDs, sizes, tokens and timings. |
| TR-SEC-8 | All third-party calls use TLS; no PII sent to the LLM beyond the minimum needed. |
| TR-SEC-9 | Generated files are served through short-lived signed URLs (e.g. 15 minutes). |
| TR-SEC-10 | Dependency scanning and Dependabot enabled; a failing audit blocks release. |
| TR-SEC-11 | Account deletion hard-deletes profile, facts, analyses and generated files. |
| TR-SEC-12 | CSP, HSTS and standard security headers set at the Next.js config level. |

---

## 16. Rate limiting and cost control

### 16.1 Layers

| Layer | Key | Purpose |
|---|---|---|
| L1 | IP | Protects unauthenticated and guest traffic |
| L2 | Clerk `user_id` | Fair use per account |
| L3 | Global daily token budget | Protects the wallet / free quota |

### 16.2 Implementation

```ts
// lib/ratelimit/index.ts
import { Ratelimit } from '@upstash/ratelimit';
import { Redis } from '@upstash/redis';

const redis = Redis.fromEnv();

export const limits = {
  analyze:  new Ratelimit({ redis, limiter: Ratelimit.slidingWindow(20, '1 h') }),
  chat:     new Ratelimit({ redis, limiter: Ratelimit.slidingWindow(60, '1 h') }),
  generate: new Ratelimit({ redis, limiter: Ratelimit.slidingWindow(10, '1 d') }),
  parseCv:  new Ratelimit({ redis, limiter: Ratelimit.slidingWindow(5,  '1 h') }),
};

// DISABLED when process.env.RATE_LIMIT_ENABLED === 'false' (dev/test only)
```

### 16.3 Requirements
- **TR-RL-1** `RATE_LIMIT_ENABLED=false` disables all layers (development and testing only; never honored in production).
- **TR-RL-2** Every 429 includes `Retry-After` and a localized explanation.
- **TR-RL-3** Global budget: when `Σ cost_est` for the day exceeds `DAILY_TOKEN_BUDGET`, switch to degraded mode (cheap model only) and notify the user in-UI.
- **TR-RL-4** When the hard cap (`DAILY_TOKEN_HARD_CAP`) is hit, return `503` with a localized message and a link to the status page; do not silently fail.
- **TR-RL-5** Cost is computed per call from a versioned price table (`lib/llm/pricing.ts`), so a provider price change is a one-line diff.
- **TR-RL-6** Payload caps: posting ≤ 20,000 chars, CV text ≤ 100,000 chars, chat message ≤ 2,000 chars.
- **TR-RL-7** Identical postings are cached by `jd_hash`; a cache hit costs zero tokens.
- **TR-RL-8** Only retrieved facts (not the entire profile) are sent to the LLM.

### 16.4 Bring Your Own Key (BYO-key)

Implements RF-15.22–RF-15.27.

- **TR-RL-9** A user may store one provider key (`user_api_keys`). When present and valid, the L2 (per-user) and L3 (budget) limits are skipped for that user's calls. The L1 (IP) limit still applies, as a blunt protection against scripted abuse.
- **TR-RL-10** Keys are encrypted with AES-256-GCM using `BYO_KEY_ENCRYPTION_KEY` (32 bytes, base64). The plaintext key lives in server memory only for the duration of a request.
- **TR-RL-11** Keys are never logged, never returned to the client after creation, and never included in error messages or telemetry. The API exposes `provider` and `key_hint` only.
- **TR-RL-12** If a BYO call fails with 401/403/429 from the provider, the request surfaces a localized error. **Silent fallback to the platform key is forbidden**, so the platform is never charged for a user's failed key.
- **TR-RL-13** BYO calls are written to `usage_events` with `cost_source = 'byo_key'`; `cost_est` is recorded for observability but excluded from the global budget sum.
- **TR-RL-14** Deleting a stored key takes effect immediately and returns the user to platform-key quotas.

---

## 17. Internationalization

### 17.1 Model

Two independent language axes — this distinction is critical:

| Axis | Decided by | Applies to |
|---|---|---|
| **UI language** | User preference (switchable anytime) | Interface, chat copy, errors, emails |
| **CV language** | Language of the job posting | Generated document content |

A user browsing in Spanish may generate an English CV for an English posting, and vice versa.

### 17.2 Implementation

- `next-intl` with an App Router `[locale]` segment (`/es/...`, `/en/...`).
- Middleware resolves locale: explicit user preference → cookie → `Accept-Language` → **`es` fallback**.
- Message catalogs: `messages/es.json`, `messages/en.json`. Adding a locale must touch only those files plus `lib/i18n/locales.ts`.
- **TR-I18N-1** No user-facing string may be hardcoded in a component; a lint rule rejects bare JSX text in `app/**` and `components/**`.
- **TR-I18N-2** Locale persists across sessions (profile field for users, cookie/localStorage for guests).
- **TR-I18N-3** Switching locale preserves in-progress state (chat, form drafts) and does not re-run LLM calls.
- **TR-I18N-4** Dates and numbers render with `Intl.DateTimeFormat` / `Intl.NumberFormat`.
- **TR-I18N-5** LLM prompts take a `locale` parameter; question wording is generated in the UI language, while CV bullet wording follows the CV language.
- **TR-I18N-6** Section headings in the generated CV come from `format_spec.headings[cvLang]`.
- **TR-I18N-7** Spanish is the default: root `/` redirects to `/es` unless a preference states otherwise.
- **TR-I18N-8** Error messages, empty states and validation copy are localized for both locales before launch.

---

## 18. Observability

| Signal | Where | Retention |
|---|---|---|
| `usage_events` | Supabase | 90 days |
| Structured app logs | Vercel logs | Plan default |
| Rejected-bullet events | Supabase (`unverified_count`, reason) | 90 days |
| Cost dashboard | Internal admin route | — |
| Error tracking | Free tier of a provider (to be chosen) | — |

Key metrics to expose internally:
- hallucination rate = rejected bullets / total bullets
- tokens per generation, cost per CV
- average confidence at generation, % forced
- pagination iterations per document
- provider failure rate per model

---

## 19. Testing strategy

| Level | Scope | Tooling |
|---|---|---|
| Unit | Fact-locking validator, confidence scorer, pagination math, format spec serialization | Vitest / pytest |
| Contract | zod schemas accept valid and reject invalid LLM payloads | Vitest |
| Integration | Pipeline with a **mocked LLM provider** (deterministic fixtures) | Vitest |
| Golden files | Known profile + posting ⇒ expected content tree | pytest |
| Pagination | Fixture documents must converge to exactly 1 page | pytest |
| E2E | Sign-up → profile → posting → chat → download | Playwright |
| i18n | Every key exists in both locales; no missing or orphan keys | Custom CI check |

**TR-TEST-1** Fact-locking must have a test that injects a hallucinated number and asserts the bullet is rejected.
**TR-TEST-2** The pagination engine must have a test asserting `page_count == 1` for the default spec across a corpus of real profiles.
**TR-TEST-3** CI fails if any locale key is missing in either language.

---

## 20. CI/CD and deployment

```yaml
# .github/workflows/ci.yml (sketch)
on: [push, pull_request]
jobs:
  web:
    - pnpm install --frozen-lockfile
    - pnpm lint              # includes the no-hardcoded-string rule
    - pnpm typecheck
    - pnpm test              # unit + contract
    - pnpm test:i18n         # locale key parity
  docgen:
    - pip install -r services/docgen/requirements.txt
    - pytest services/docgen
  deploy:
    needs: [web, docgen]
    if: github.ref == 'refs/heads/main'
    # Vercel Git integration performs the deploy
```

- Preview deployments for every PR; production on `main`.
- Migrations applied through `supabase/migrations` in order; never edited after merge.
- Feature flags in env (`RATE_LIMIT_ENABLED`, `DEGRADED_MODE`, `ENABLE_GUEST_MODE`).

---

## 21. Environment variables

```env
# Auth
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=
CLERK_SECRET_KEY=

# Supabase
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=          # server only

# LLM providers (only the ones in use)
GROQ_API_KEY=
GEMINI_API_KEY=
OPENROUTER_API_KEY=

# LLM routing
# Only ZDR-approved providers (backend_schema.md §8.1).
LLM_ROUTE_EXTRACT_PROFILE=groq:openai/gpt-oss-120b
LLM_ROUTE_ANALYZE_JD=groq:openai/gpt-oss-120b
LLM_ROUTE_GAP_QUESTIONS=groq:openai/gpt-oss-120b
LLM_ROUTE_REWRITE_BULLETS=groq:openai/gpt-oss-120b
LLM_ROUTE_CLASSIFY_FACTS=groq:openai/gpt-oss-120b
LLM_FALLBACK_CHAIN=groq

# Limits and cost
RATE_LIMIT_ENABLED=true
CONFIDENCE_THRESHOLD=0.95
DAILY_TOKEN_BUDGET=
DAILY_TOKEN_HARD_CAP=
PAYLOAD_MAX_JD_CHARS=20000
PAYLOAD_MAX_CV_CHARS=100000

# BYO-key (RF-15.22–RF-15.27)
BYO_KEY_ENCRYPTION_KEY=             # 32 bytes, base64; required if BYO-key is enabled
ENABLE_BYO_KEY=true

# Upstash
UPSTASH_REDIS_REST_URL=
UPSTASH_REDIS_REST_TOKEN=

# Docgen service
CHROME_BIN=                         # headless Chromium/Edge for previews; auto-detected locally
DOCGEN_URL=
DOCGEN_SHARED_SECRET=               # bearer token for POST /docgen; keep it server-side

# Feature flags
ENABLE_GUEST_MODE=true
DEGRADED_MODE=false
```

**TR-ENV-1** Any variable without a safe default must fail fast at boot with a clear message, not at first request.
**TR-ENV-2** `.env.example` is committed; real values never are.

---

## 22. Performance budgets

| Operation | Budget (p95) |
|---|---|
| Posting analysis | < 8 s |
| Chat round (streamed first token) | < 1.5 s |
| Full generation (excluding user time) | < 30 s |
| Docgen service call | < 10 s |
| Profile parse | < 12 s |
| Cold start (docgen) | < 3 s |

---

## 23. Open technical decisions

1. **Embeddings vs keyword retrieval** for fact selection: start with keyword/BM25; add embeddings only if quality demands it.
2. **Streaming transport**: Server-Sent Events vs Vercel AI SDK streams for chat.
3. **Docgen hosting**: whether the HTML-replica approach (§12.1, option A) is faithful enough, or the service must move to a separate container host with LibreOffice (option B). **Highest-risk infrastructure decision in the project.**
4. **Automated provider health checks** to reorder the fallback chain dynamically.
5. **Initial LLM provider**: still open (PRD §21.2). The adapter layer is built first so the choice can be made at M1 with no rework.

Resolved since the previous revision: PDF export (deferred, decision 2), guest identity (cookie, decision 1), preview fidelity (image from docgen, decision 6).

---

## 24. Traceability (PRD → technical)

| PRD requirement | Technical implementation |
|---|---|
| RF-2.2 client-side extraction | pdf.js / mammoth.js in the browser |
| RF-4 confidence gate | §10 confidence scorer + pipeline state machine |
| RF-5.1 fact-locking | §9 validator, enforced again in `GenerateRequestSchema` |
| RF-6 fixed format | §11 `format_spec` with global default row |
| RF-8 i18n | §17 `next-intl`, dual-axis language model |
| RF-15.1–15.6 rate limiting | §16 Upstash layers + `RATE_LIMIT_ENABLED` |
| RF-15.11–15.13 prompt injection | TR-SEC-1, TR-SEC-2 |
| RF-15.21 no CV binary storage | TR-SEC-5 |
