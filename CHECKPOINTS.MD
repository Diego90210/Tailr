# CHECKPOINTS — Final State Evaluation

> In multi-agent systems, the path is not evaluated; the destination is.
>
> These are the objective checkpoints that a judge (human or AI) can use to determine whether the project is healthy.

## C1 — The Harness Is Complete

* [ ] The base files exist: `AGENTS.md`, `init.sh`, `feature_list.json`, `TASKS.md`, `progress/current.md`, `progress/history.md`.
* [ ] The 3 harness docs exist: `docs/architecture.md`, `docs/conventions.md`, `docs/verification.md`.
* [ ] The 4 project docs exist: `docs/PRD.md`, `docs/technical_requirements.md`, `docs/app_flow.md`, `docs/backend_schema.md`.
* [ ] `./init.sh` finishes with `[OK] Environment ready` (exit code 0).

## C2 — The State Is Consistent

* [ ] At most one feature is `in_progress` or `review` in `feature_list.json` (zero is also valid).
* [ ] Every feature whose status is `done` has tests that pass.
* [ ] Project-wide coverage debt is tracked as a `pending` feature in `feature_list.json`, not silently accepted.
* [ ] `progress/current.md` contains only the template, or describes the active session — no stale content from a previous session.

## C3 — The Code Respects the Architecture

* [ ] No LLM provider SDK is imported outside `lib/llm/providers/` — the abstraction boundary is intact.
* [ ] `services/docgen/` is deterministic: the same content tree plus the same `format_spec` produce byte-identical output, and formatting/pagination never pass through the LLM.
* [ ] Every table has RLS enabled, and every mutation performs a server-side ownership check derived from the Clerk JWT (never from client input).
* [ ] No secret literal in any file; no CV, posting, or chat content in logs or telemetry.
* [ ] No debug `print()`/`console.log` outside pipeline progress output, no `TODO`/`FIXME` without context.

## C4 — Verification Is Real

* [ ] The fact-locking validator test exists and **rejects a hallucinated number** (an injected metric not present in the referenced facts).
* [ ] The pagination test asserts `page_count == 1` for the default `format_spec` across the fixture corpus.
* [ ] The i18n parity check passes: no user-facing key exists in only one of `es`/`en`.
* [ ] `pnpm test` and `python -m pytest` (docgen) report > 0 tests and all pass.
* [ ] Tests are pure: no Supabase, Clerk, Upstash, or LLM network calls; integration checks run in `./init.sh` or CI.

## C5 — The Session Was Closed Properly

* [ ] No suspicious untracked files; `git status --short` shows only intended changes.
* [ ] No secrets or generated artifacts (`.docx`, preview PNGs) tracked in git — `.gitignore` excludes them and `git ls-files` proves it.
* [ ] `progress/history.md` contains an entry for the latest session; the old content is no longer in `progress/current.md`.
* [ ] The latest feature worked on is reflected with the correct status in `feature_list.json`.
* [ ] If the plan changed structurally, `feature_list.json` was regenerated from `TASKS.md` (`scripts/build_feature_list.py`) and both stay consistent.
* [ ] `docs/` is consistent with what the session changed (any decision change updates the corresponding companion document).

---

## How to Use This File

A reviewer agent (`agents/reviewer.md`) goes through each checkbox, marks `[x]` or `[ ]`, and rejects the session closure if any boxes remain unchecked in C1–C5.

Commands the reviewer runs (from the project root):

```bash
./init.sh                                  # everything: env, files, tests, lint, build, i18n
pnpm test                                  # Vitest unit/contract tests
python -m pytest services/docgen -q        # docgen tests (from services/docgen)
git status --short                         # dirty-tree check
```
