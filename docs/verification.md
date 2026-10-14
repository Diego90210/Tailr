# Verification — How to Demonstrate That the Work Works

> Golden rule: **the agent does not say "it works"; it demonstrates it**.
>
> Every task must end with executable evidence, not assertions.

## Verification Levels

### Level 1 — Unit Tests (mandatory)

Every public function in `lib/` and `services/docgen/` must have at least one test that:

1. Covers the happy path.
2. Covers at least one error path if the function can fail.

Commands:

```bash
pnpm test                                  # TypeScript (Vitest)
python -m pytest services/docgen -q        # Python (docgen)
```

### Level 2 — Build + Lint + i18n (mandatory for any frontend change)

Any change to `apps/web/`, `components/`, `lib/` or `messages/` must pass all gates:

```bash
pnpm lint
pnpm build
pnpm test:i18n
```

All must exit 0. A TypeScript error, a lint warning, or a missing locale key fails verification.

### Level 3 — Pipeline Smoke Test (mandatory for pipeline/LLM/docgen tasks)

Run the real flow end-to-end against the mock provider (deterministic, no network):

```bash
# posting → analysis → gap chat → generation → docgen
pnpm test:pipeline
```

Then verify the concrete output, not just the exit code:

* The analysis returns `must` and `nice` requirements and a match score between 0 and 100.
* Confidence moves when a gap is answered.
* The generated document reports `page_count == 1` and a `fill_pct` between 0.90 and 0.98.
* `unverified_count` is 0, or every rejected bullet has a logged reason.

### Level 4 — Manual Smoke Test (optional but recommended)

Before closing the session, start the dev server and click through the affected route:

```bash
pnpm dev
# /es/start → paste → answer → preview → download
# Confirm no console errors and that switching to /en preserves state
```

## Tailr-specific evidence

These are the claims that must be provable, not asserted:

| Claim | Evidence required |
|---|---|
| The app never invents a fact | A test injects a hallucinated number and asserts the bullet is **rejected** |
| The output is one page | A test asserts `page_count == 1` across the fixture corpus |
| Formatting is deterministic | Rendering the same tree twice yields identical output |
| Both languages work | `pnpm test:i18n` passes and the flow was exercised in `es` and `en` |
| The LLM is swappable | The pipeline test runs green against the mock provider with no code change |
| Users cannot read each other's data | An ownership test proves user B receives zero rows for user A |
| No content leaks to logs | A test greps emitted logs for fixture content and finds none |

## Anti-Patterns (Do Not Do)

* ❌ "I added the endpoint, it should work." → executable test or build output is missing.
* ❌ A test that only verifies the function does not raise. → it must assert the concrete result.
* ❌ Mocking the fact validator to make a generation test pass. → the validator is the point of the product.
* ❌ Marking a feature `done` without `./init.sh` passing.
* ❌ Claiming the one-page guarantee from a visual glance instead of the measured `page_count`.
* ❌ Adding a locale string to `es` only and leaving `en` for later.

## Final Verification Before Closing

```bash
./init.sh    # must finish with [OK] — files, feature_list.json, tests, lint, build, i18n
```

If `./init.sh` fails, **do not** mark anything as `done`. Record the blocker in `progress/current.md` and set the feature's `status` to `blocked` in `feature_list.json`.
