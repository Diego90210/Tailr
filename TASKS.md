# TASKS — Tailr Implementation Plan

**One CV. Every job.**

| Field | Value |
|---|---|
| Version | 0.1 (draft) |
| Companion documents | `PRD.md`, `technical_requirements.md`, `app_flow.md`, `backend_schema.md` |
| Scope | Requirement breakdown into executable tasks with priority, status, dependencies and traceability |
| Status of this document | Living document — update the Status column as work progresses |

---

## 1. How to use this document

Every task is small enough to finish in one sitting, has a single verifiable outcome, and points back to the requirement it satisfies. If a task cannot be tied to a requirement, either the requirement is missing or the task is unnecessary.

**Workflow rules**

1. **Spikes first.** Two unknowns can invalidate the architecture. They are resolved before any product code is written.
2. **Critical path in order.** Tasks marked **P0** form the spine; everything else can be reordered freely.
3. **One task, one PR.** If a task needs two PRs, split it.
4. **Status is updated in the same PR** that changes it.
5. **No task is "done" without its test** where a test is specified.

---

## 2. Legends

### Status

| Code | Meaning |
|---|---|
| `TODO` | Not started |
| `WIP` | In progress |
| `BLOCKED` | Cannot proceed; reason noted |
| `REVIEW` | Implemented, awaiting review or verification |
| `DONE` | Merged and verified |

### Priority

| Code | Meaning |
|---|---|
| **P0** | Critical path. Blocks other work. |
| **P1** | Required for the MVP. |
| **P2** | Required for v1 (public, multi-user). |
| **P3** | v1.1 / v2. Not needed to launch. |

### Estimate

| Code | Rough size |
|---|---|
| `XS` | A few hours |
| `S` | About a day |
| `M` | 2–3 days |
| `L` | About a week |
| `XL` | More than a week — split it |

### Refs
Abbreviations: `RF-*` = PRD functional requirement · `TR-*` = technical requirement · `§n` = section of the referenced document · `P0–P16` = screen in `app_flow.md` · `D-*` = data element in `backend_schema.md`.

---

## 3. Progress overview

| Phase | Milestone | Tasks | Done |
|---|---|---|---|
| 0 | Spikes + foundations | 13 | 0 |
| 1 | Data layer | 10 | 0 |
| 2 | LLM layer | 10 | 0 |
| 3 | Profile | 8 | 0 |
| 4 | Posting analysis | 5 | 0 |
| 5 | Gap chat | 8 | 0 |
| 6 | Generation + format | 14 | 0 |
| 7 | Security + limits | 12 | 0 |
| 8 | Privacy + lifecycle | 8 | 0 |
| 9 | Internationalization | 7 | 0 |
| 10 | Guest mode | 4 | 0 |
| 11 | Observability | 3 | 0 |
| 12 | QA + launch | 9 | 0 |
| — | Documentation (already delivered) | 4 | **4** |

**Total: 111 implementation tasks**, plus 4 documentation artifacts already delivered.

---

## 4. Milestones (from the PRD)

| # | Milestone | Exit criterion | Unlocked by |
|---|---|---|---|
| M0 | Repo, license, CI, structure | Skeleton deployed on Vercel | Phase 0–1 |
| M1 | LLM layer + prompts + schemas | Working `analyze` | Phase 2 + 4 |
| M2 | Manual profile + form | Profile persisted in Supabase | Phase 3 |
| M3 | Gap chat | Conversation with computed confidence | Phase 5 |
| M4 | Generation + format engine | A one-page `.docx` | Phase 6 |
| M5 | Rate limiting + cost telemetry | Safe public usage | Phase 7 |
| M6 | CV upload + autofill | Complete onboarding | Phase 3 (PROF-04…07) |

---

## 5. Critical path

```
SPIKE-01 (preview rendering risk)
   └─► SPIKE-02 (provider limits) ──► SETUP-* ──► DATA-01…07 ──► LLM-01…08
          └─► JD-01…03 ──► CHAT-01…05 ──► GEN-01…06 ──► DOC-01…03 ──► GEN-07…08
                 └─► RL-01 ──► TEST-05 ──► LAUNCH-01
```

Anything not on this chain can be parallelized.

---

## 6. Phase 0 — Spikes and foundations

### Spikes (do these first)

| ID | Task | Pri | Status | Est | Depends | Refs |
|---|---|---|---|---|---|---|
| `SPIKE-01` | **Prove one-page fidelity**: render a real CV content tree to `.docx` with python-docx, then produce a preview image via both a headless-Chromium HTML replica and a LibreOffice container. Compare page count, line breaks and `fill_pct`. Decide option A vs B (`technical_requirements.md` §12.1). | **P0** | DONE | L | — | TR-FMT-1…5, §12.1 |
| `SPIKE-02` | **Validate Groq as primary**: confirm ZDR is available and self-serve on the free tier, measure real rate limits (RPM/TPM), and verify JSON-schema structured output reliability on the target model. Record results. | **P0** | DONE | S | — | §8.1, RF-11.4 |
| `SPIKE-03` | **Structured-output reliability**: run 20 real prompts through the chosen model and measure schema-validation failure rate. If > 5%, add a repair step or change model. | **P0** | DONE | S | SPIKE-02 | RF-11.4 |
| `SPIKE-04` | **Client-side parsing feasibility**: verify `pdf.js` + `mammoth.js` extract usable text from 10 real CVs (including a scanned one, to confirm the failure path is detectable). | **P1** | TODO | S | — | RF-2.2, RF-2.4 |

### Foundations

| ID | Task | Pri | Status | Est | Depends | Refs |
|---|---|---|---|---|---|---|
| `SETUP-01` | Repo skeleton: Next.js App Router + TypeScript + Tailwind + shadcn/ui. Structure per `technical_requirements.md` §4. | **P0** | DONE | M | SPIKE-01 | §4 |
| `SETUP-02` | Python docgen service skeleton (`services/docgen`) with a health endpoint. | **P0** | DONE | S | SETUP-01 | §12 |
| `SETUP-03` | CI: lint, typecheck, unit tests (web + docgen), locale-parity check. Fails the build on any of them. | **P0** | DONE | M | SETUP-01,02 | TR-TEST-3 |
| `SETUP-04` | Env contract: `.env.example` + boot-time validation that fails fast with a clear message. | **P0** | DONE | S | SETUP-01 | TR-ENV-1,2 |
| `SETUP-05` | `LICENSE` (MIT), `CONTRIBUTING.md`, `README.md` with local setup. | **P1** | TODO | S | SETUP-01 | PRD §18 |
| `SETUP-06` | Deploy the skeleton to Vercel (web + docgen), functions pinned to `iad1`. Verify the live URL. | **P0** | DONE | S | SETUP-02 | §18.1 |
| `SETUP-07` | Supabase project created with region pinned to `us-east-1`; `supabase/migrations` wired to CI. | **P0** | TODO | S | SETUP-01 | §18.1 |
| `SETUP-08` | Clerk application configured; middleware protects app routes and leaves `/start` public. | **P0** | TODO | M | SETUP-01 | RF-1.1, §14 |
| `SETUP-09` | Upstash Redis provisioned; region co-located with the functions. | **P1** | TODO | XS | SETUP-06 | §16 |

---

## 7. Phase 1 — Data layer

| ID | Task | Pri | Status | Est | Depends | Refs |
|---|---|---|---|---|---|---|
| `DATA-01` | Migration: `profiles`, `facts`, `experience`, `projects`, `education`, `certifications`. | **P0** | TODO | M | SETUP-07 | §5.1 |
| `DATA-02` | Migration: `format_specs` + seed the global default (Cambria, name 15pt, body 11pt, italic dates, `#0563C1` links). | **P0** | TODO | S | DATA-01 | §11.1, RF-6.2 |
| `DATA-03` | Migration: `job_analyses`, `questions`, `conversations`. | **P0** | TODO | M | DATA-01 | §5.1 |
| `DATA-04` | Migration: `generated_cvs`, `usage_events`, `user_api_keys` (incl. `cost_source`, `key_ciphertext`). | **P0** | TODO | M | DATA-01 | §5.1, §11 |
| `DATA-05` | RLS policies on **every** table, using `auth.jwt()->>'sub'`; `usage_events` server-insert only. | **P0** | TODO | M | DATA-01…04 | §5.2, §7 |
| `DATA-06` | Clerk ↔ Supabase integration: pass the Clerk JWT to Supabase and verify RLS sees the `sub`. | **P0** | TODO | M | SETUP-08, DATA-05 | §14 |
| `DATA-07` | TS types + zod contracts for profile, analysis and generation (`lib/contracts`). | **P0** | TODO | M | DATA-01 | §6 |
| `DATA-08` | Repository/service layer with server-side ownership checks (defense in depth beyond RLS). | **P0** | TODO | M | DATA-06,07 | §7 |
| `DATA-09` | Retention job: age-out per `backend_schema.md` §15 (30d analyses/CVs, 7d guest) + `keep_my_data` flag on `profiles`. | **P2** | TODO | M | DATA-01 | §15 |
| `DATA-10` | RLS + ownership verification tests (user B cannot read user A). | **P0** | TODO | S | DATA-06 | §22 |

---

## 8. Phase 2 — LLM layer

| ID | Task | Pri | Status | Est | Depends | Refs |
|---|---|---|---|---|---|---|
| `LLM-01` | Provider interface + `TaskKind` + request/response types. No SDK import outside `lib/llm/providers`. | **P0** | DONE | S | SETUP-01 | RF-11.1 |
| `LLM-02` | Groq adapter with JSON-schema structured output. | **P0** | DONE | M | LLM-01, SPIKE-02 | RF-11.4 |
| `LLM-03` | Task router driven by env (`LLM_ROUTE_*`), no recompilation to change models. | **P0** | DONE | S | LLM-02 | RF-11.2 |
| `LLM-04` | Cascade fallback chain with failure classification (rate limit / timeout / upstream). | **P1** | TODO | M | LLM-03 | RF-11.3 |
| `LLM-05` | Cost meter + versioned pricing table (`lib/llm/pricing.ts`). | **P1** | TODO | S | LLM-02 | TR-RL-5 |
| `LLM-06` | Write a `usage_events` row on every call (provider, model, tokens, cost, latency). | **P1** | TODO | S | LLM-05, DATA-04 | RF-11.5 |
| `LLM-07` | Migrate the existing skills into `prompts/*.md` (analyze-jd, extract-profile, gap-questions, rewrite-bullets, diagnose-ats, humanizer). | **P0** | DONE | M | SETUP-01 | RF-11.6 |
| `LLM-08` | Validate every LLM response with zod before use; invalid output never reaches the user or the DB. | **P0** | TODO | S | DATA-07 | RF-11.4 |
| `LLM-09` | Deterministic mock provider for tests and local development. | **P1** | TODO | S | LLM-01 | §19 |
| `LLM-10` | **Enable ZDR** in the provider console and add a startup assertion that no training-enabled configuration is used. | **P0** | DONE | XS | SPIKE-02 | §8.1 |

---

## 9. Phase 3 — Profile

| ID | Task | Pri | Status | Est | Depends | Refs |
|---|---|---|---|---|---|---|
| `PROF-01` | Profile CRUD API (`POST/GET/PATCH /api/profile`), zod-validated, ownership-checked. | **P0** | TODO | M | DATA-08 | RF-2.5 |
| `PROF-02` | Profile editor UI — accordion sections, inline add/edit, autosave with debounce, unsaved-change guard. | **P0** | TODO | L | PROF-01 | P4 |
| `PROF-03` | Fact model in the UI: every bullet shows provenance (`cv_upload` / `user_input` / `chat_answer`) and is independently editable. | **P1** | TODO | M | PROF-02 | RF-2.6, P4 |
| `PROF-04` | Client-side extraction: `pdf.js` for PDF, `mammoth.js` for DOCX, MIME/size validation, no binary upload. | **P1** | TODO | M | SPIKE-04 | RF-2.1,2.2 |
| `PROF-05` | `extract_profile` prompt + `POST /api/profile/parse` returning a partial profile, per-field confidence and `undetected[]`. | **P1** | TODO | M | LLM-08, PROF-04 | RF-2.3,2.4 |
| `PROF-06` | Undetected-fields UI: explicit list of what could not be read, each linking to the exact field. | **P1** | TODO | M | PROF-05 | RF-2.4, P3 |
| `PROF-07` | Onboarding screens P2 and P3 (upload vs manual, progress, error states incl. scanned PDF). | **P2** | TODO | M | PROF-06 | P2, P3 |
| `PROF-08` | Profile strength indicator (completeness %, fact count, open gaps) — a nudge, never a blocker. | **P3** | TODO | S | PROF-02 | P4 |

---

## 10. Phase 4 — Posting analysis

| ID | Task | Pri | Status | Est | Depends | Refs |
|---|---|---|---|---|---|---|
| `JD-01` | `analyze_jd` prompt: must/nice split, keyword kinds, language, seniority, red flags, company and role title. | **P0** | TODO | M | LLM-08 | RF-3.2 |
| `JD-02` | `POST /api/analyze` endpoint, payload caps (20k chars), persistence to `job_analyses`. | **P0** | TODO | M | JD-01, DATA-03 | RF-3.1 |
| `JD-03` | Deterministic match score (must 70% / nice 30%) computed in code, never by the LLM. | **P0** | TODO | S | JD-02 | RF-3.3 |
| `JD-04` | Posting-only cache keyed by `jd_hash`: caches requirements/keywords/language but **never** match score or coverage. | **P1** | TODO | M | JD-03 | §13.3 |
| `JD-05` | Language handling: detect ES/EN; if `other`, ask which CV language to use. | **P1** | TODO | S | JD-02 | RF-3.4, RF-8.5 |

---

## 11. Phase 5 — Gap chat

| ID | Task | Pri | Status | Est | Depends | Refs |
|---|---|---|---|---|---|---|
| `CHAT-01` | Coverage classification per requirement: COVERED / PARTIAL / UNKNOWN, using retrieved facts only. | **P0** | TODO | M | JD-03 | §7.2 |
| `CHAT-02` | Confidence scorer: weighted formula, threshold fixed at 0.95, blocking rule for `must` gaps. | **P0** | TODO | S | CHAT-01 | §10, RF-4.1 |
| `CHAT-03` | `gap_questions` prompt: max 4 questions per round, in the **UI language**, only about gaps. | **P0** | TODO | M | LLM-08 | RF-4.2,4.3 |
| `CHAT-04` | `POST /api/chat` streaming endpoint; transcript persisted. | **P0** | TODO | M | CHAT-03 | RF-4.6 |
| `CHAT-05` | Answers persisted as facts with `provenance = chat_answer`; confidence recomputed on each answer. | **P0** | TODO | S | CHAT-04 | RF-4.4 |
| `CHAT-06` | "No / Skip" semantics: closes the gap as `none` and never fills it with a guess. | **P0** | TODO | S | CHAT-05 | RF-4.5 |
| `CHAT-07` | P6 UI: analysis panel with status badges, live confidence meter, chat panel, action bar. | **P0** | TODO | L | CHAT-04 | P6 |
| `CHAT-08` | Force-generate path: secondary CTA, persistent warning, records `forced = true`. | **P1** | TODO | S | CHAT-07 | RF-4.1, P6 |

---

## 12. Phase 6 — Generation and format *(highest technical risk)*

| ID | Task | Pri | Status | Est | Depends | Refs |
|---|---|---|---|---|---|---|
| `GEN-01` | Section selection and ordering by relevance to the posting. | **P0** | TODO | M | CHAT-02 | §8.2 |
| `GEN-02` | `rewrite_bullets` prompt: XYZ formula, every bullet returns `factIds[]`. | **P0** | TODO | M | GEN-01 | RF-5.4 |
| `GEN-03` | **Fact-locking validator**: reject empty/unknown `fact_id`, reject numbers not present in referenced facts, reject bullets over 220 chars. | **P0** | TODO | M | GEN-02 | RF-5.1, §9.2 |
| `GEN-04` | Humanizer pass, then **re-run the numeric check** (rewriting can introduce numbers). | **P0** | TODO | S | GEN-03 | §9.2 step 3 |
| `GEN-05` | Suggested-facts queue: inferred facts go to the user as a question, never into the CV. | **P1** | TODO | M | GEN-03 | RF-5.2 |
| `GEN-06` | Content tree builder producing the `GenerateRequest` payload (validated with `min(1)` factIds per bullet). | **P0** | TODO | M | GEN-04 | §6 |
| `DOC-01` | docgen: python-docx builder driven entirely by `format_spec` (fonts, sizes, italic dates, hyperlinks, tab stops). | **P0** | DONE | L | SPIKE-01 | §11.2, RF-14.4 |
| `DOC-02` | Pagination measurement with real font metrics (Pillow + font file); returns `fill_pct`, `line_count`. | **P0** | DONE | M | DOC-01 | TR-FMT-2 |
| `DOC-03` | Convergence loop: compress when > 0.98, enrich when < 0.90, max iterations, explicit overflow warning. | **P0** | DONE | M | DOC-02 | §11.2, TR-FMT-1 |
| `DOC-04` | Preview image rendering per the SPIKE-01 decision; return `preview_png_b64`. | **P0** | DONE | M | SPIKE-01, DOC-03 | §12.1, RF-5.6 |
| `DOC-05` | Fidelity test: same content tree through docx and preview ⇒ equal page count and line breaks. | **P1** | TODO | M | DOC-04 | §12.1 |
| `DOC-06` | `POST /docgen` endpoint with shared-secret auth; keep it off the public path. | **P0** | DONE | S | DOC-03 | §12 |
| `GEN-07` | P7 UI: preview image, metrics strip, checks panel, and **per-bullet traceability** to `fact_id` + provenance. | **P0** | TODO | L | DOC-06 | P7, RF-5.1 |
| `GEN-08` | Download endpoint with short-lived signed URLs (15 min), ownership-checked. | **P0** | TODO | S | GEN-07, DATA-04 | TR-SEC-9 |

---

## 13. Phase 7 — Security and limits

| ID | Task | Pri | Status | Est | Depends | Refs |
|---|---|---|---|---|---|---|
| `SEC-01` | Treat posting + CV text as untrusted data: explicit delimiters, system-prompt statement, never instructions. | **P0** | DONE | S | LLM-07 | TR-SEC-1 |
| `SEC-02` | Injection detection and logging (role reassignment, "ignore previous instructions"). | **P1** | TODO | S | SEC-01 | TR-SEC-2 |
| `SEC-03` | Payload caps and file validation (posting 20k, CV text 100k, chat 2k, file 5 MB). | **P0** | TODO | S | JD-02 | TR-RL-6 |
| `SEC-04` | Security headers (CSP, HSTS) at the Next.js config level. | **P2** | TODO | S | SETUP-01 | TR-SEC-12 |
| `SEC-05` | Log-redaction lint rule + test proving no content field can be logged. | **P1** | TODO | M | LLM-06 | TR-SEC-7 |
| `RL-01` | Three rate-limit layers: IP, Clerk user, global daily budget (Upstash). | **P0** | TODO | M | SETUP-09 | RF-15.1,2,3 |
| `RL-02` | `429` responses with `Retry-After` and localized copy. | **P1** | TODO | S | RL-01 | RF-15.5 |
| `RL-03` | Global budget: degraded mode at `DAILY_TOKEN_BUDGET`, `503` kill switch at the hard cap. | **P1** | TODO | M | RL-01, LLM-05 | RF-15.4 |
| `RL-04` | `RATE_LIMIT_ENABLED=false` bypass, honored in dev/test only and never in production. | **P1** | TODO | XS | RL-01 | RF-15.6, TR-RL-1 |
| `RL-05` | BYO-key: AES-256-GCM storage, write-only API, `key_hint`, test button, **no silent fallback**. | **P2** | TODO | L | DATA-04, RL-01 | RF-15.22…27 |
| `RL-06` | Retrieval-limited prompting: send only relevant facts, never the whole profile. | **P1** | TODO | M | CHAT-01 | TR-RL-8 |
| `SEC-06` | Secret audit: no provider key or service-role key reachable from the client bundle. | **P0** | TODO | S | LLM-02 | TR-SEC-3 |

---

## 14. Phase 8 — Privacy and lifecycle

| ID | Task | Pri | Status | Est | Depends | Refs |
|---|---|---|---|---|---|---|
| `PRIV-01` | Delete flows: single CV, profile (cascade), account (hard delete + Clerk). Double confirmation. | **P1** | TODO | M | DATA-04 | RF-7.3, §16 |
| `PRIV-02` | Data export: JSON (profile, facts, analyses) + generated `.docx` files. | **P2** | TODO | M | PRIV-01 | §16.3 |
| `PRIV-03` | Privacy page in ES and EN: what is stored, what is not, subprocessor list, international transfer disclosure. | **P1** | TODO | M | I18N-02 | P12, §18.2 |
| `PRIV-04` | Terms page in ES and EN. | **P2** | TODO | S | I18N-02 | P12 |
| `PRIV-05` | Consent capture at sign-up with a Ley 1581-shaped *autorización* + *aviso de privacidad* link. | **P1** | TODO | M | SETUP-08 | §21 |
| `PRIV-06` | Archive each subprocessor DPA in `/legal/dpas/` with retrieval date; record countersignature status. | **P3** | TODO | S | — | §8, §23.2 |
| `PRIV-07` | Settings page P9: language, usage counters, data export/delete. | **P2** | TODO | M | PRIV-01 | P9 |
| `PRIV-08` | *Keep my data* toggle wired to `DATA-09`, off by default and reversible. | **P2** | TODO | S | DATA-09, PRIV-07 | §15 |

---

## 15. Phase 9 — Internationalization

| ID | Task | Pri | Status | Est | Depends | Refs |
|---|---|---|---|---|---|---|
| `I18N-01` | `next-intl` setup with `[locale]` segment; middleware resolves preference → cookie → `Accept-Language` → **`es`**. | **P0** | TODO | M | SETUP-01 | RF-8.1,2, TR-I18N-7 |
| `I18N-02` | `messages/es.json` and `messages/en.json` for every screen. Spanish is authored first. | **P0** | TODO | L | I18N-01 | RF-8.4 |
| `I18N-03` | Locale switcher that preserves route, query and in-progress state, triggering **no** LLM call. | **P1** | TODO | M | I18N-01 | TR-I18N-3, AC-6 |
| `I18N-04` | **Dual-axis language logic**: UI language vs CV language (from the posting); section headings from `format_spec.headings[cvLang]`. | **P0** | TODO | M | I18N-01, DOC-01 | RF-8.5, TR-I18N-5,6 |
| `I18N-05` | Locale-aware dates and numbers via `Intl.*`. | **P3** | TODO | XS | I18N-01 | TR-I18N-4 |
| `I18N-06` | Lint rule rejecting hardcoded user-facing strings in `app/**` and `components/**`. | **P1** | TODO | M | I18N-02 | TR-I18N-1 |
| `I18N-07` | CI locale-parity check; the build fails if a key is missing in either language. | **P1** | TODO | S | I18N-02 | TR-TEST-3 |

---

## 16. Phase 10 — Guest mode

| ID | Task | Pri | Status | Est | Depends | Refs |
|---|---|---|---|---|---|---|
| `GUEST-01` | Signed, HttpOnly `guest_session` cookie + guest session record; no Clerk anonymous accounts. | **P1** | TODO | M | DATA-01 | decision 1 |
| `GUEST-02` | Hard profile requirement gate on `/start`, blocking modal, pasted posting preserved in `localStorage`. | **P1** | TODO | S | PROF-01, GUEST-01 | decision 4, P5 |
| `GUEST-03` | Guest gate modal (P14) triggered on download, never before the first generation completes. | **P1** | TODO | M | GUEST-01 | P14 |
| `GUEST-04` | Migration on sign-up: re-key guest facts, answers and the generated CV to the new `sub`. | **P1** | TODO | M | GUEST-03 | RF-1.3, §10 |

---

## 17. Phase 11 — Observability

| ID | Task | Pri | Status | Est | Depends | Refs |
|---|---|---|---|---|---|---|
| `OBS-01` | Admin usage dashboard (allowlist, returns 404 to others): cost/day, provider failure rate, p95 latency. | **P3** | TODO | M | LLM-06 | P15 |
| `OBS-02` | Quality metrics: hallucination rate (rejected bullets / total), forced-generation rate, pagination iterations per document. | **P2** | TODO | M | GEN-03 | §18 |
| `OBS-03` | Error tracking on a free tier, with content scrubbing. | **P3** | TODO | S | SEC-05 | §18 |

---

## 18. Phase 12 — QA and launch

| ID | Task | Pri | Status | Est | Depends | Refs |
|---|---|---|---|---|---|---|
| `TEST-01` | Unit: fact-locking validator (incl. an injected hallucinated number being rejected), confidence scorer, pagination math. | **P0** | TODO | M | GEN-03, CHAT-02 | TR-TEST-1 |
| `TEST-02` | Contract: zod schemas accept valid and reject invalid LLM payloads. | **P0** | TODO | S | DATA-07 | §19 |
| `TEST-03` | Integration: full pipeline against the mock provider with deterministic fixtures. | **P1** | TODO | M | LLM-09 | §19 |
| `TEST-04` | Golden files: known profile + posting ⇒ expected content tree. | **P1** | TODO | M | GEN-06 | §19 |
| `TEST-05` | E2E (Playwright): guest path (paste → answer → preview → gate) and returning-user path. | **P0** | TODO | L | GUEST-04, GEN-08 | AC-1,2 |
| `TEST-06` | Accessibility pass: keyboard-only completion, focus rings, live regions on chat, AA contrast. | **P2** | TODO | M | CHAT-07 | §7 |
| `TEST-07` | Responsive pass: P6 with stacked panels and a chat bottom sheet on mobile. | **P2** | TODO | M | CHAT-07 | §7 |
| `QA-01` | Verify acceptance criteria AC-1…AC-10 from `app_flow.md` §9 and record evidence. | **P0** | TODO | M | TEST-05 | AC-1…10 |
| `LAUNCH-01` | Pre-launch checklist: ZDR enabled, regions pinned, rate limits live, retention job running, privacy page published in ES, DPAs archived. | **P0** | TODO | S | QA-01 | §22, §23 |

---

## 19. Definition of Done (applies to every task)

A task is `DONE` only when **all** of the following hold:

1. Code merged to `main` with review.
2. Its specified test exists and passes; if no test is specified, the PR states why.
3. Lint, typecheck and the full CI suite pass.
4. Any new user-facing string exists in **both** `es` and `en`.
5. No new secret, no new PII in logs, and no new content field in telemetry.
6. If it touches the data model: RLS policy included **and** an ownership test added.
7. If it touches the LLM layer: provider-agnostic (no SDK import outside `lib/llm/providers`).
8. If it touches formatting: the one-page guarantee still holds on the fixture corpus.
9. The Status column in this document is updated in the same PR.
10. Any companion document (`PRD.md`, `technical_requirements.md`, `app_flow.md`, `backend_schema.md`) is updated if the task changed a decision.

---

## 20. Pre-launch checklist

| # | Item | Owner | Done |
|---|---|---|---|
| 1 | ZDR enabled in the LLM provider console | — | ⬜ |
| 2 | Supabase region pinned to `us-east-1`; Vercel functions to `iad1` | — | ⬜ |
| 3 | Rate limits live in production (`RATE_LIMIT_ENABLED=true`) | — | ⬜ |
| 4 | Global budget and kill switch tested with a synthetic burst | — | ⬜ |
| 5 | Retention age-out job running on schedule | — | ⬜ |
| 6 | Privacy page published in Spanish with the subprocessor list and transfer disclosure | — | ⬜ |
| 7 | Consent flow reviewed against Ley 1581 requirements | — | ⬜ |
| 8 | DPAs archived in `/legal/dpas/` | — | ⬜ |
| 9 | One-page fidelity verified across a corpus of real profiles | — | ⬜ |
| 10 | Hallucination rate measured at 0 rejected-but-shipped bullets over the test corpus | — | ⬜ |
| 11 | No secret reachable from the client bundle | — | ⬜ |
| 12 | Both locales complete; CI parity check green | — | ⬜ |

---

## 21. Suggested working order (first two weeks)

If the goal is to reach a demonstrable prototype as fast as possible:

| Day | Work |
|---|---|
| 1–2 | `SPIKE-01`, `SPIKE-02` — resolve the two risks that can change the architecture |
| 3–4 | `SETUP-01`…`SETUP-08` — skeleton, CI, Supabase, Clerk, deploy |
| 5–6 | `DATA-01`…`DATA-08` — schema, RLS, contracts, Clerk↔Supabase |
| 7–8 | `LLM-01`…`LLM-08` — provider layer, router, prompts, validation |
| 9 | `JD-01`…`JD-03` — first end-to-end LLM feature (analysis) |
| 10–11 | `CHAT-01`…`CHAT-05` — the confidence loop, the product's core |
| 12–14 | `DOC-01`…`DOC-03` — a real one-page `.docx` from a real profile |

At the end of day 14 the app should produce a tailored `.docx` from a pasted posting, with no UI polish. That is the minimum convincing demo.

---

## 22. Open items carried from other documents

| Source | Item | Blocks |
|---|---|---|
| `PRD.md` §21.2 | Domain name | Launch only |
| `backend_schema.md` §23.2 | DPA countersignature per provider | Launch only |
| `app_flow.md` §10 | — (all resolved) | — |
| `technical_requirements.md` §23 | PDF export deferred to v2; docgen hosting depends on `SPIKE-01` | v2 |
