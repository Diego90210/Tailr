# Architecture — What "Doing a Good Job" Means

> This document defines the quality standard. Reviewer agents evaluate code against this file. If it is not stated here, it is not a requirement.

## Principles

1. **Clear layers.** The project has four layers, and only four:

   * **Frontend** — `apps/web/` (App Router pages), `components/` (shared UI), `lib/supabase/` (client), `messages/` (locales). React Server Components by default; client components only for interactive surfaces.
   * **Application core** — `lib/llm/` (provider abstraction), `lib/pipeline/` (orchestrator + state machine), `lib/facts/` (fact-locking), `lib/scoring/` (confidence and match score), `lib/ratelimit/`, `lib/contracts/` (zod). All TypeScript.
   * **Document generation** — `services/docgen/` (Python). Renders `.docx` and measures pagination. Deterministic.
   * **Data** — Supabase Postgres with RLS, ownership derived from the Clerk JWT.

   Do not introduce additional layers (extra service classes, repositories, queues) until there is a concrete reason documented in `feature_list.json`.

2. **The LLM is a replaceable component.** The product is the structure around it: the profile, fact-locking, and the deterministic format engine. No provider SDK may be imported outside `lib/llm/providers/`. Model selection is configuration (`LLM_ROUTE_*`), never code.

3. **Fact-locking is the product.** No generated text may contain a fact, number, metric, date or technology that does not exist in the user's profile. A bullet without a `fact_id` is discarded. A question is always better than an invention.

4. **Formatting is deterministic and never goes through the LLM.** `services/docgen/` turns a validated content tree plus a `format_spec` into a one-page document. Same input ⇒ byte-identical output.

5. **Explicit errors.** Python functions that can fail raise named exceptions (`CannotFitOnePage`, `MissingEnvVar`). TypeScript boundaries return typed results. Never return `None`/`undefined` to signal failure, and never let a silent fallback change behaviour.

6. **RLS everywhere, plus a server check.** All tables have Row Level Security enabled with ownership resolved from `auth.jwt()->>'sub'`. Every mutation additionally performs an explicit ownership check in the route handler. Two lines of defense, not one.

7. **Every byte from a user is hostile.** Posting text and CV text are delimited and labelled as data. They are never instructions, and their content never reaches a log.

8. **Cost is a first-class concern.** Every LLM call writes a `usage_events` row. Rate limiting is layered (IP, user, global budget). Cache only what is not profile-derived.

9. **Two languages, always.** Spanish is the default (primary market); English is first class. No change ships with a string in only one locale.

## Data Flow

```text
Browser
  ├─ paste posting ─────────────────────────────┐
  └─ upload CV → pdf.js / mammoth.js (local) ───┤ text only, never the binary
                                                ▼
                        Next.js route handlers (pipeline orchestrator)
                                  │
        ┌─────────────────────────┼──────────────────────────┐
        ▼                         ▼                          ▼
  lib/llm (providers)      lib/facts + lib/scoring      Supabase (RLS)
  analyze · extract        validate · confidence        profiles · facts
  chat · rewrite           match score                  analyses · CVs
        │                         │                          │
        └────────────► validated content tree ◄──────────────┘
                                  │
                                  ▼
                    services/docgen (python-docx + Pillow)
                       render → measure → converge
                                  │
                                  ▼
                        .docx + preview PNG  (signed URLs)
```

## The one-page guarantee

The format engine renders, measures with real font metrics, and iterates:

```text
render → measure fill_pct → if > 0.98 compress lower-priority bullets
                          → if < 0.90 allow enrichment
                          → repeat (bounded) → return page_count
```

Word and LibreOffice paginate differently. The measurement is authoritative; a rendering is only a secondary check.

## Boundaries

| Boundary | Rule |
|---|---|
| `lib/llm/providers/` | The only place a provider SDK may be imported |
| `services/docgen/` | No LLM, no database, no business logic |
| `lib/contracts/` | The only place schemas are defined; all boundaries import from here |
| `prompts/` | The only place prompt text lives |
| `supabase/migrations/` | Append-only; never edit a merged migration |

## What NOT to Do

* Do not import a provider SDK outside `lib/llm/providers/`.
* Do not ask the LLM to format, lay out, or paginate a document.
* Do not emit a bullet, number, or technology that is not backed by a `fact_id`.
* Do not silently repair or drop a validation failure without logging it.
* Do not fall back to a provider whose free tier trains on content — even when the primary is down.
* Do not write to Supabase from a React component; the frontend is read-only under RLS.
* Do not store the uploaded CV binary, in any bucket, at any time.
* Do not log CV, posting, or chat content, or any name, email or phone number.
* Do not ship a user-facing string in one language only.
* Do not add a table without RLS and an ownership test.
* Do not use `console.log` for debugging in committed code; use structured logging without content.
