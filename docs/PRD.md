# PRD — Tailr

**One CV. Every job.**

| Field | Value |
|---|---|
| Version | 0.1 (draft) |
| Status | Proposal |
| License | MIT |
| Business model | Public product, free to use |
| Stack | Next.js + Python · Supabase · Clerk · Vercel |
| Primary market | Spanish-speaking users |
| UI languages | Spanish and English (switchable at any time) |

---

## 1. Executive summary

Tailr is an open web application where anyone can paste a job posting and get a CV tailored to that posting: honest, ATS-friendly and ready to send. Unlike existing tools, it **does not invent**. When a fact is missing, it asks through a chat and waits for the answer before writing anything.

The value is not in the language model. It is in three pieces we control: the **structured master profile**, **fact-locking**, and the **deterministic format engine** that guarantees a one-page document in the user's exact layout.

---

## 2. Problem

1. Tailoring a CV per posting takes 30–60 minutes, so almost nobody does it.
2. Current AI tools produce inflated CVs: they invent metrics, technologies and achievements.
3. An inflated CV collapses in the interview and burns the candidate.
4. Good CVs already exist, but they live in hard-to-reuse formats (PDF, DOCX with arbitrary layouts).

---

## 3. Goals and non-goals

### Goals (v1)
- **G1.** Cut CV tailoring time from ~45 minutes to under 5 minutes.
- **G2.** Guarantee **zero invented facts**: everything in the generated CV exists in the user's profile.
- **G3.** Produce a **one-page** `.docx` in a faithful, ATS-safe format.
- **G4.** Run at **zero or marginal cost** on free tiers.
- **G5.** Be deployable and maintainable by a single person.

### Non-goals (v1)
- Job search, vacancy matching or automatic applying.
- Multiple visual templates (v1 uses one fixed format; the data model keeps the door open).
- Cover letters, LinkedIn optimization, interview prep (later phases).
- Native mobile apps.
- Monetization: the product is free and MIT-licensed, with no plans or payments.

---

## 4. Users

| Persona | Description | Primary need |
|---|---|---|
| **P1 · Power user** | Developer in active search, applying to 10–15 postings | Already has a profile and a format; wants speed |
| **P2 · Outdated-CV job seeker** | Has one or several old CVs | Upload a CV and have the system build the profile |
| **P3 · Recent graduate** | Little experience, thin CV | Detect gaps and help articulate what they do have |

**Primary market:** Spanish-speaking job seekers. All default copy, onboarding and documentation start in Spanish, with English as a first-class alternative.

---

## 5. Success metrics

| Metric | Definition | v1 target |
|---|---|---|
| Time to first CV | From pasting the posting to downloading | < 5 min |
| Verified-fact rate | % of bullets with a valid `fact_id` | **100%** |
| Gaps resolved via chat | % of UNKNOWN fields the user answers | > 70% |
| Page utilization | Fill % reported by the pagination engine | 92–98% |
| Cost per CV | Tokens × price | ≈ $0 (free tier) |
| Profile extraction | % of form fields auto-filled from an uploaded CV | > 60% |

---

## 6. Scope by phase

| Phase | Content | Exit criterion |
|---|---|---|
| **MVP** | Auth, manual profile, paste posting, analysis, gap chat, generate `.docx` | Generate 5 real CVs with no factual errors |
| **v1** | Master CV upload + autofill + undetected-field detection; history; rendered preview | A third party generates their CV unaided |
| **v1.1** | Hardened rate limiting, **BYO-key**, quota dashboard, cost telemetry | Survives public use without burning free tiers |
| **v2** | Configurable format (UI), **PDF export**, cover letter, detailed ATS score | — |

---

## 7. User flows

### F1 · Profile onboarding (with master CV)
```
Upload CV (PDF/DOCX) → text extraction (client-side)
  → LLM structures it into the profile schema
  → prefilled form + list of fields NOT detected
  → user corrects/completes
  → save profile
```
The "not detected" list is explicit: *"I could not extract these sections from your CV (likely because of its format): projects, dates for X, certifications."*

### F2 · Tailor a CV to a posting
```
Paste posting (text or URL)
  → analysis: must/nice requirements, keywords, match score
  → gap analysis against the profile
  → chat: questions only about gaps
  → confidence ≥ threshold
  → fact-locked writing → format engine → one page
  → download .docx
```

### F3 · History
View generated CVs, re-download, regenerate with a different format.

---

## 8. Functional requirements

### RF-1 · Authentication
- RF-1.1 Clerk as the provider (email + OAuth).
- RF-1.2 A user may own 1..N master profiles.
- RF-1.3 Guest mode: **one generation without an account**, then login is required. The guest result is preserved if the user signs up afterwards.

### RF-2 · Master profile
- RF-2.1 Upload a master CV in **PDF and DOCX**, max 5 MB.
- RF-2.2 Text extraction happens **client-side** with `pdf.js` and `mammoth.js` (avoids serverless limits and avoids uploading the binary).
- RF-2.3 The LLM converts the text into the profile schema with a **confidence score per field**.
- RF-2.4 Fields below the threshold (proposed 0.7) are flagged **NOT DETECTED** and highlighted in the form.
- RF-2.5 The form is always editable; whatever the user types is the **source of truth**.
- RF-2.6 Every fact stores provenance: `cv_upload` | `user_input` | `chat_answer`.

### RF-3 · Posting analysis
- RF-3.1 Input: **pasted job posting text**, copied by the user from any job board. No URL scraping in v1.
- RF-3.2 Structured output: `must` / `nice` requirements, keywords by type (technical / soft / tool / domain), posting language, seniority, red flags.
- RF-3.3 Weighted match score (must 70% / nice 30%).
- RF-3.4 Language detection → determines the generated CV language.

### RF-4 · Clarification chat (product core)
- RF-4.1 The system **blocks generation** until confidence ≥ 95% or the user explicitly chooses "generate anyway".
- RF-4.2 Questions are generated **only** about gaps, in the user's UI language.
- RF-4.3 At most N questions per round (proposed 4) to avoid overwhelming the user.
- RF-4.4 Every answer is persisted as a fact with `provenance = chat_answer`.
- RF-4.5 The user can answer "not applicable / I don't have it", closing the gap as `none` (never filled with a guess).
- RF-4.6 The conversation history is visible and reproducible.

### RF-5 · CV generation
- RF-5.1 **Fact-locking:** every generated bullet must reference one or more `fact_id`s. A bullet with no associated fact is **discarded** and logged.
- RF-5.2 New facts the LLM infers go to a **suggestion queue**, never directly into the CV.
- RF-5.3 Section selection and ordering based on relevance to the posting.
- RF-5.4 Bullets follow the XYZ formula and pass through the `humanizer` skill (no AI tics, no em dashes).
- RF-5.5 Output `.docx`. PDF export is **deferred** to v2 (decision 2).
- RF-5.6 The generated CV is previewed as an **image rendered by the docgen service**, not live HTML, so the preview is faithful to the downloadable file (decision 6).

### RF-6 · Format
- RF-6.1 A **fixed default format** whose specification is stored as data (`format_spec`).
- RF-6.2 `format_spec` includes: font, name size, body size, italic dates, margins, line spacing, section order, section headings.
- RF-6.3 v1 exposes no configuration UI, but **the data model already supports it** (explicit requirement).
- RF-6.4 The engine guarantees **one page** through the measurement loop (see §14).

### RF-7 · History and export
- RF-7.1 Persist every generation with its analysis and fill %.
- RF-7.2 Re-download at no token cost.
- RF-7.3 Delete profile and all associated generations.

### RF-8 · Internationalization (i18n)
- RF-8.1 The UI is available in **Spanish and English** and switchable at any time without losing state.
- RF-8.2 Default language is derived from the browser's `Accept-Language`, **falling back to Spanish**, the primary market.
- RF-8.3 The language preference is persisted per user (and in `localStorage` for guests).
- RF-8.4 All UI strings are externalized in locale files; no hardcoded copy in components.
- RF-8.5 **The generated CV language is independent of the UI language**: it follows the language of the job posting.
- RF-8.6 Chat questions and clarification copy are rendered in the user's UI language, regardless of the posting language.
- RF-8.7 Dates and numbers shown in the UI are locale-aware.
- RF-8.8 Spanish is the primary market: onboarding, docs, error messages and support copy default to Spanish.
- RF-8.9 Adding a new locale must not require changes outside the locale files and the locale registry.

---

## 9. The 95% rule (core requirement)

This is the differentiator. It is implemented as follows:

```
1. Map posting requirements → profile facts
2. Classify each requirement: COVERED | PARTIAL | UNKNOWN
3. confidence = weighted_covered / weighted_total
4. If confidence < 0.95  ⇒  generate questions and BLOCK
5. Answers ⇒ new facts (provenance = chat_answer) ⇒ recompute
6. Only then write
```

**System invariant:** no generated text may contain a fact, number, metric, date or technology that does not exist in the profile. This invariant is validated in the final step (§RF-5.1) and is the reason the product exists.

---

## 10. System architecture

```
┌────────────────────────── Browser (Next.js) ──────────────────────────┐
│  • CV upload: pdf.js / mammoth.js (local extraction)                  │
│  • Profile form, chat, preview                                        │
│  • Clerk session                                                      │
└──────────────┬───────────────────────────────────────┬────────────────┘
               │ server actions / fetch                │
┌──────────────▼───────────────────────────────────────▼────────────────┐
│                     Next.js (Vercel) — API / logic                    │
│  /api/profile  /api/analyze  /api/chat  /api/generate  /api/cv/[id]   │
│  • Rate limiting (Upstash Ratelimit)  • Validation (zod)              │
│  • Pipeline orchestration             • Feature flags                 │
└──────┬──────────────────────┬──────────────────────┬──────────────────┘
       │                      │                      │
┌──────▼───────┐   ┌──────────▼─────────┐   ┌────────▼──────────────────┐
│ Supabase     │   │ LLM layer (abstr.) │   │ Python service (Vercel)   │
│ Postgres+RLS │   │ adapters + router  │   │ python-docx + paginator   │
│ Storage      │   │ (Groq/Gemini/…)    │   │ (one page)                │
└──────────────┘   └────────────────────┘   └───────────────────────────┘
```

**Key decision:** formatting and pagination **never** go through the LLM. They are code.

---

## 11. LLM abstraction layer (explicit requirement)

> "The LLM can change; it doesn't matter. The structure around it is what matters."

A single interface isolates the rest of the system from the provider:

```ts
interface LLMProvider {
  name: string;
  complete<T>(req: {
    task: TaskKind;          // 'extract_profile' | 'analyze_jd' | 'chat' | 'rewrite'
    messages: Message[];
    schema?: JSONSchema;     // structured output
    maxTokens: number;
    temperature: number;
  }): Promise<T>;
  estimateCost(req): number;
}
```

Requirements:
- **RF-11.1** No module outside `lib/llm/**` imports a provider SDK.
- **RF-11.2** Routing by task (`task → model`) is configurable through environment variables, without recompiling.
- **RF-11.3** **Cascading fallback**: if provider A fails or runs out of quota, fall back to B, then C.
- **RF-11.4** All outputs are validated against a **JSON Schema** (zod) before use.
- **RF-11.5** Per-call logging: provider, model, input/output tokens, estimated cost, latency.
- **RF-11.6** All prompts live in `prompts/` as versioned Markdown (current skills migrate here).
- **RF-11.7** Switching providers must not require touching business logic.

---

## 12. Data model (Supabase / Postgres)

```
profiles(id, user_id, name, contact_json, languages, format_spec_id, created_at)
facts(id, profile_id, kind, text, metrics_json, provenance, verified_at)
experience(id, profile_id, company, role, start, end, fact_ids[])
projects(id, profile_id, name, stack, url, fact_ids[])
skills / education / certifications
format_specs(id, owner_id null = global, spec_json)
job_analyses(id, profile_id, jd_text, jd_lang, requirements_json, keywords_json,
             match_score, red_flags_json, created_at)
questions(id, analysis_id, text, status, answer, fact_id, created_at)
conversations(id, analysis_id, messages_json)
generated_cvs(id, analysis_id, docx_path, pdf_path, fill_pct, unverified_count, created_at)
usage_events(id, user_id, task, provider, model, tokens_in, tokens_out, cost_est, created_at)
```

Rules:
- **RLS enabled on every table**: a user only sees their own rows.
- `format_specs` with `owner_id = null` is the global default format.
- `usage_events` is the source of truth for cost control and budget-based rate limiting.

---

## 13. API

| Method | Route | Description | Limit |
|---|---|---|---|
| POST | `/api/profile/parse` | CV text → structured profile + undetected fields | 5/h |
| POST | `/api/profile` | Create/update profile | 30/h |
| POST | `/api/analyze` | Posting → structured analysis | 20/h |
| POST | `/api/chat` | Clarification round (streaming) | 60/h |
| POST | `/api/generate` | Generate docx + rendered preview image | 10/h |
| GET | `/api/cv/[id]` | Download | 60/h |

Cross-cutting rules:
- **zod** validation at the boundary.
- Size limits: posting ≤ 20,000 characters; CV text ≤ 100,000.
- Clear error codes (`429` with `retry_after`).

---

## 14. Format and pagination engine

Reuses the already-proven approach (`cv_builder.py` + `measure_cv.py`):

```
1. Render content using the format_spec
2. Measure lines with real font metrics (Pillow + font file)
3. fill = content_height / usable_height
4. If fill > 0.98 → request compression of lower-priority bullets → back to 2
5. If fill < 0.90 → allow enriching bullets → back to 2
6. Output: docx + fill_pct + line count
```

Requirements:
- **RF-14.1** The result must be exactly **1 page**.
- **RF-14.2** Target utilization 92–98%.
- **RF-14.3** Caveat: Word and LibreOffice paginate differently. Measure with font metrics; never trust a single renderer.
- **RF-14.4** Default format (Diego's current one): Cambria, name 15 pt bold, body 11 pt, italic dates, `#0563C1` underlined hyperlinks, margins 0.3/0.5 in.

---

## 15. Security, rate limiting and cost control

### 15.1 Rate limiting
- **RF-15.1** Two layers: per **user** (Clerk ID) and per **IP** (for guests).
- **RF-15.2** Implemented with **Upstash Ratelimit** (free tier) over Redis.
- **RF-15.3** Default quotas: 10 generations/day, 60 chat messages/day, 20 analyses/day.
- **RF-15.4** Global daily token budget: when exceeded, **degrade** (cheap model only) then **kill switch** with a clear message.
- **RF-15.5** `429` responses include `Retry-After` and a human-readable message, never a generic error.
- **RF-15.6** `RATE_LIMIT_ENABLED=false` environment flag for development and testing (explicit requirement).

### 15.2 Token abuse
- **RF-15.7** Per-request token budget with pre-truncation when exceeded.
- **RF-15.8** Only relevant facts are sent to the LLM (retrieval), never the whole profile.
- **RF-15.9** Cache identical posting analyses (text hash).
- **RF-15.10** Reuse analyses already produced for the same URL/text by the same user.

### 15.3 Prompt injection *(real risk: the posting is third-party text)*
- **RF-15.11** Posting and CV text are **always treated as data**, never as instructions: delimited and explicitly labelled in the prompt.
- **RF-15.12** The system never executes actions or changes role based on instructions contained in a posting.
- **RF-15.13** Typical injection patterns are detected, logged and neutralized.

### 15.4 Other
- **RF-15.14** API keys server-side only; never in the client bundle.
- **RF-15.15** File type and size validated before processing.
- **RF-15.16** RLS in Supabase; no cross-user access.
- **RF-15.17** Account and data deletion on request.
- **RF-15.18** Logs never contain sensitive content (no CV or posting text in clear).

### 15.5 Privacy
- **RF-15.19** Clear privacy policy: what is stored, where and for how long.
- **RF-15.20** User data is never used to train models; prefer zero-retention providers.
- **RF-15.21** The uploaded original CV is **not** stored as a binary; only the extracted text and the profile.

### 15.6 Bring Your Own Key (BYO-key)
- **RF-15.22** A user may supply their own LLM API key to bypass the shared rate limits and quotas.
- **RF-15.23** BYO keys are encrypted at rest, never logged, never included in telemetry, and never returned to the client after saving (write-only field, displayed masked).
- **RF-15.24** With a valid BYO key, per-user quotas (RF-15.3) and the global daily budget (RF-15.4) do not apply to that user's requests. Protections that exist to protect *other* users still apply in full: payload caps, schema validation, prompt-injection defenses and the fact-locking invariant.
- **RF-15.25** BYO-key requests are recorded in `usage_events` with `cost_source = 'byo_key'`; no cost is charged to the platform budget.
- **RF-15.26** An invalid, expired or out-of-quota BYO key returns a clear, localized error and **never** falls back silently to the platform key.
- **RF-15.27** v1 supports BYO keys only for providers already integrated (see §11). Adding a provider must not require a UI change.

---

## 16. Non-functional requirements

| Area | Requirement |
|---|---|
| Performance | Generation < 60 s p95 (excluding user thinking time in chat) |
| Availability | Best-effort; it is a free project and is documented as such |
| Accessibility | WCAG 2.1 AA on forms and chat |
| i18n | Spanish and English for both UI and generated CV |
| Observability | Structured logs + `usage_events`; no PII |
| Maintainability | Single maintainer; documentation lives in the repo |
| Testing | Unit tests for the format engine and fact-locking; e2e for the main flow |

---

## 17. Deployment and free-tier limits

| Service | Plan | Limit to watch | Mitigation |
|---|---|---|---|
| Vercel | Hobby | The free plan is for **non-commercial use**; function duration; bandwidth | Being free and MIT, it qualifies as non-commercial; monitor limits |
| Supabase | Free | DB size, storage, **pausing after inactivity** | Keep-alive cron; prune old CVs |
| Clerk | Free | Monthly active users | Sufficient for v1 |
| Upstash | Free | Commands/month | Lightweight rate limiting |
| LLM | Free tier | RPM/TPM, daily quotas | Provider cascade + degradation |

> Verify current plan limits before launch; free tiers change frequently.

**Implementation recommendation:** the `.docx` is generated in the Python service (python-docx is pure Python and light, so it fits in a serverless function). Heavy **PDF parsing happens client-side** to stay far from Vercel limits.

---

## 18. MIT license — implications

- Anyone may use, copy, modify and **sell** the software. If the goal is freedom, this is the right choice, and it must be accepted that others may profit from it.
- Include `LICENSE` (MIT text) and `CONTRIBUTING.md`.
- Under MIT there is **no obligation to publish modifications** (unlike GPL).
- Open decision: protecting the brand or the official hosting is handled separately from the code license.

---

## 19. Risks

| Risk | Impact | Mitigation |
|---|---|---|
| The LLM hallucinates a fact | Critical (breaks the promise) | Fact-locking + final validation + tests |
| Arbitrary CV parsing fails | High | Client-side extraction + explicit undetected-field reporting + editable form |
| Prompt injection via posting | High | Treat as data; delimiters; detection |
| Burning free tiers | Medium | Rate limiting + budget + cache + degradation |
| Word vs LibreOffice pagination mismatch | Medium | Measure with font metrics; verify in both |
| Real cost > $0 once it gets traction | Medium | Measure `cost_est` from day one; **BYO-key** (RF-15.22–RF-15.27) as the escape hatch |
| Vercel Hobby non-commercial clause | Low/Medium | Free, non-monetized product |

---

## 20. Milestones

| # | Milestone | Deliverable |
|---|---|---|
| M0 | Repo, license, CI, structure | Skeleton deployed on Vercel |
| M1 | LLM layer + prompts + schemas | Working `analyze` |
| M2 | Manual profile + form | Profile persisted in Supabase |
| M3 | Gap chat | Conversation with computed confidence |
| M4 | Generation + format engine | A one-page `.docx` |
| M5 | Rate limiting + cost telemetry | Safe public usage |
| M6 | CV upload + autofill | Complete onboarding |

---

## 21. Decisions and open questions

### 21.1 Resolved

| # | Question | Decision |
|---|---|---|
| 2 | Confidence threshold | **Fixed at 95%.** Not user-configurable. |
| 3 | Posting input | **Pasted text only.** The user copies the description from any job board; no URL scraping in v1. |
| 4 | Guest mode | **One generation without login**, then an account is required. |
| 5 | Product name | **Tailr** — *One CV. Every job.* |
| 6 | Cost escape hatch | **BYO-key.** Users who want to avoid rate limits can supply their own LLM API key (RF-15.22–RF-15.27). |
| 7 | Locale set | **Spanish and English only** for v1. |

### 21.2 Still open

1. **Domain** for the `Tailr` brand.
2. **DPA countersignature**: confirm per subprocessor whether a countersigned addendum is available on a free plan (`backend_schema.md` §23.2).

### 21.3 Newly constrained

- **LLM provider** is no longer an open preference. `backend_schema.md` §8.1 establishes **zero data retention as a hard selection criterion**. That excludes the Gemini free tier, whose unpaid-service terms allow content to be used for product improvement and model training, and points to **Groq with ZDR enabled** as the primary. Any fallback must meet the same bar; a provider that trains on free-tier content is never used for profile data, not even as a last resort.

---

## 22. Next artifacts

1. `technical_requirements.md` — technical counterpart of this document.
2. Complete Supabase SQL schema with RLS.
3. TypeScript contracts (types + zod) for profile, analysis and generation.
4. `prompts/` — current skills migrated to versioned format.
5. Repo skeleton (Next.js + Python service + CI).
