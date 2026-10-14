# SPIKE-02: LLM Provider Validation (Groq)

## 1. Objective
Confirm the suitability of Groq as the primary LLM provider based on data privacy (ZDR) and technical constraints.

## 2. Verdict (2026-10-08)

**Groq confirmed as primary.** ZDR is self-serve for all customers including free tier, the contract forbids training on inputs/outputs, and the free tier sustains 30 RPM on the target model. The binding constraint is **TPM (8K), not RPM** — budget ~11 JD-analysis calls/minute on free.

## 3. Findings

### ZDR — pass (docs + contract evidence; console toggle is the one manual step)
- [Your Data in GroqCloud](https://console.groq.com/docs/your-data): *"By default, Groq does not retain customer data for inference requests"*; reliability/abuse logs up to 30 days and **"All customers may enable Zero Data Retention (ZDR) in Data Controls settings"** — no plan/enterprise gate.
- [Groq Services Agreement §4.2](https://console.groq.com/docs/legal/services-agreement/): *"Groq is not permitted to use Inputs or Outputs for training or fine-tuning any AI Model Services or other models, unless explicitly granted permission or instructed by Customer."* Contractual, not a policy page; not tier-gated.
- DPA available with SCCs; data stored in US GCP buckets (matches `backend_schema.md` §8.1).
- **Not verifiable via API:** the actual toggle state of this account. Enable + eyeball it in [Data Controls](https://console.groq.com/settings/data-controls) — tracked as **LLM-10**.

### Rate limits — measured on `openai/gpt-oss-120b` (free plan)
| Source | Value |
|---|---|
| `x-ratelimit-limit-requests` (= RPD per docs) | **1000/day** |
| `x-ratelimit-limit-tokens` (= TPM per docs) | **8000/min** |
| Docs published free-tier limits for this model | 30 RPM / 1K RPD / 8K TPM / 200K TPD |
| Burst: 40 requests, 8 workers, 3.1 s | **30 × 200, then 10 × 429**, zero other errors |
| `retry-after` on 429 | **2 s** |
| Latency (probe) | 1.09 s; structured calls 1.0–1.3 s |

- 429 handling is clean and fast (`retry-after: 2`); a small retry-with-backoff layer is sufficient (LLM-04).
- Real workload math: one JD-analysis call = 346 prompt + 331 completion tokens (226 of them **reasoning** tokens) ≈ 677 tokens → **~11 calls/min under the 8K TPM cap**. RPM 30 is never the binding limit for our payloads. Escalation path if it bites: BYO-key (RF-15.22) or Developer plan — never a training-capable provider (`backend_schema.md` §8.1).

### Structured output — pass (strict mode)
- `response_format.type = "json_schema"` with **`strict: true`** works: constrained decoding, guaranteed schema match.
- 5/5 calls validated against a pydantic model (JD-analysis shaped schema: enum fields, arrays, `additionalProperties: false`), **failure rate 0%**.
- Strict-mode requirements: every field `required`, `additionalProperties: false`. Supported on `openai/gpt-oss-120b`, `openai/gpt-oss-20b`, `qwen/qwen3.8-27b`.
- The 20-prompt failure-rate measurement is **SPIKE-03**, not here.

## 4. Evidence
- Raw report: `scripts/spike_output/spike02_report.json` (probe headers, 5 structured rows with usage, burst results) — gitignored.
- Harness: `scripts/spike02_groq.py` (`python scripts/spike02_groq.py`, ~2 min, ~45 API calls).

## 5. Consequences for the plan
- **LLM-02**: use JSON-schema structured output with `strict: true`; schema must be all-required + `additionalProperties: false`.
- **LLM-04**: retry on 429 honoring `retry-after` (observed 2 s); TPM, not RPM, is the metric to watch.
- **LLM-10**: manual — flip ZDR in Data Controls and record it (only item not provable from here).
- **SPIKE-03**: unblocked.

## 6. Status
- ID: `SPIKE-02`
- Status: DONE
- Priority: P0
- Est: S
