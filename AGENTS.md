# Tailr — Agent Instructions

Paste a job posting, get a tailored, honest, one-page CV. The core is fact-locking, an LLM abstraction layer, and a deterministic document generator.

## 1. Before you begin (mandatory)

1. Read `progress/current.md` to see where the last session ended.
2. Read `feature_list.json` and choose ONE feature with status `pending`. Do not work on more than one feature at a time.

## 2. Repository map

| File / Folder | What it contains | When to read it |
|---|---|---|
| `feature_list.json` | **Operative task list.** Every feature with `status`, `priority`, `depends_on`, `refs` and `acceptance` | Start of every session — pick your feature |
| `TASKS.md` | Human-readable reference plan: the detailed source this JSON is generated from | When you need the full scope or context behind a feature |
| `progress/current.md` | Live session log — task, start time, plan, notes | Start of session; update continuously while working |
| `progress/history.md` | Completed session summaries (append-only) | Start of session — avoid repeating past work |
| `docs/` | `PRD.md`, `technical_requirements.md`, `app_flow.md`, `backend_schema.md`, plus `architecture.md`, `conventions.md`, `verification.md` | When you don't know something — search here first |
| `apps/web/` | Next.js App Router pages, i18n routing, components | Working on frontend UI |
| `lib/llm/` | Provider abstraction (`providers/` only) — no SDK imports elsewhere | Working on the LLM layer |
| `lib/pipeline/` | Orchestrator + state machine | Working on the end-to-end flow |
| `lib/facts/` | Fact-locking and validation | Working on generation or anti-hallucination |
| `lib/scoring/` | Confidence and match-score computation | Working on analysis |
| `lib/ratelimit/` | Upstash rate-limit layers and quotas | Working on limits/cost |
| `lib/contracts/` | zod schemas for profile, analysis, generation | Working on any boundary |
| `services/docgen/` | Python document generator + pagination | Working on `.docx` output |
| `prompts/` | Versioned Markdown prompts | Changing any LLM behavior |
| `supabase/migrations/` | Schema and RLS policies | Changing the data model |
| `.env.example` | Environment contract (fail-fast at boot) | Checking variable names only |
| `AGENTS.md` | This file — session rules and lifecycle | Every session |

## 3. Hard rules (non-negotiables)

- **One feature at a time.** Do not mix changes from various features in the same session.
- **Do not declare a feature as `done` without green tests and `./init.sh`.** Run the test file indicated for the feature; it must pass at 100%.
- **Document what you do in `progress/current.md` while you work**, not at the end of the session.
- **Leave the repository clean.** Before closing the session: no temporary files, no debug `print()`/`console.log`, no TODOs without context.
- **If you don't know something, search `docs/` first** before making something up.

Tailr-specific rules:

- **LLM abstraction.** No provider SDK import outside `lib/llm/providers/`. Switching providers must never require touching business logic.
- **Fact-locking.** Every generated bullet must reference one or more `fact_id`s. Never invent a metric, date, technology or fact. A bullet that fails validation is discarded, not silently fixed.
- **Prompt injection.** Posting text and CV text are **data**, never instructions. They are delimited and never executed as directives.
- **i18n.** Every user-facing string must exist in both `es` and `en`. No hardcoded copy in components.
- **Secrets and PII.** No secret literals in any file. No CV, posting or chat content in logs or telemetry.
- **RLS.** Any new table ships with Row Level Security and an ownership test.
- **One page.** Any change to the format engine must keep the one-page guarantee on the fixture corpus.
- **Zero data retention.** Never add a provider whose free tier trains on content. The primary is Groq with ZDR enabled.

## 4. How to choose a feature

1. Open `feature_list.json`.
2. Filter by `status == "pending"`.
3. Sort by priority (`P0` → `P3`); among equals, prefer the **lowest `id`** whose `depends_on` features are already `done`.
4. Change its status to `in_progress`.
5. Note in `progress/current.md`: feature `id`/`key`, start time, short plan.

Never have more than one feature in `in_progress` or `review` at a time.

## 5. Session closing (lifecycle)

1. Run the indicated test file. Must pass 100%.
2. Run `./init.sh`. Must finish `[OK] Environment ready`.
3. If the feature is done: set `"status": "done"` in `feature_list.json`.
4. Move the summary from `progress/current.md` to the end of `progress/history.md`.
5. Blank `progress/current.md`, leaving just the template.
6. Remove any temporary files, debug prints, or context-free TODOs.

## 6. If you block

- Reread the relevant section of `docs/`.
- If a tool does not do what you expect, **do not work around it**: document the blockage in `progress/current.md`, set `"status": "blocked"` in `feature_list.json`, and stop the session.

## Stack reference

- **Frontend:** Next.js App Router + TypeScript + Tailwind CSS + shadcn/ui, `next-intl` (es default / en).
- **Auth:** Clerk (JWT forwarded to Supabase).
- **Database:** Supabase Postgres — RLS on every table, ownership via `auth.jwt()->>'sub'`.
- **Cache / limits:** Upstash Redis (rate limiting + posting-only cache).
- **LLM:** provider adapters behind one interface; primary **Groq with Zero Data Retention**; task router + cascade fallback via env.
- **Docgen:** Python 3.11 in `services/docgen/` — `python-docx` + `Pillow`.

## Commands

```bash
# Frontend (from repo root)
pnpm dev           # dev server
pnpm build         # production build
pnpm lint          # ESLint (includes the no-hardcoded-string rule)
pnpm test          # Vitest unit/contract tests
pnpm test:i18n     # locale-parity check (es/en)

# Docgen
cd services/docgen
python -m pytest -q

# Full gate
./init.sh
```

## Conventions (summary)

- **RLS on all tables** — ownership is always derived from the Clerk JWT, never from client input; a server-side ownership check doubles as defense in depth.
- **LLM outputs are zod-validated** before they touch the database or the user.
- **Fact-locking over fluency** — a rejected bullet is logged, never repaired silently.
- **Deterministic formatting** — docgen is code, never the LLM.
- **ES/EN parity** — a string in one language blocks merge until it exists in both.
