# SPIKE-03: Structured-Output Reliability

## 1. Objective
Run 20 real prompts through the chosen model (`openai/gpt-oss-120b`) in strict JSON-schema mode and measure the schema-validation failure rate. **Gate: > 5% ⇒ add a repair step or change model.**

## 2. Verdict (2026-10-08)

**PASS — 0 / 20 failures (0%). No repair step needed, no model change needed.**

## 3. Findings

### Failure rate (the gate)
| Run | max_tokens | Calls | Failures | Rate |
|---|---|---|---|---|
| First run (misconfigured) | **400** | 20 | 12 | 60% → gate would FAIL |
| Final run | **1000** | 20 | **0** | **0% → PASS** |

- Every failure in the first run was an API-level `400 json_validate_failed`, almost all with
  `failed_generation: "max completion tokens reached before generating a valid document"`.
- **Root cause: my config, not the model.** `gpt-oss` reasons before emitting JSON (~230 reasoning tokens measured in SPIKE-02); `max_tokens=400` truncated the document mid-generation, and strict mode correctly refuses invalid JSON.
- **Rule for LLM-02:** for structured calls on `gpt-oss`, budget `max_tokens ≥ 1000` (prompt + ~300 reasoning + output). Under-provisioning manifests as `400`, not a validation error on our side — easy to misdiagnose as model unreliability.

### Quality spot-check (valid ≠ garbage)
3 ad-hoc re-prints of extracted objects (short ES posting, bullet-list ES posting, junior EN posting): correct `role_title`, `seniority`, `language` enums, and plausible `must_have` items in the posting's own language (ES postings → `language: "es"`). Strict mode constrains *shape*, not *sense* — the spot-check is the cheap guard; a full semantic rubric belongs to LLM-05, not here.

### Performance / cost (free tier)
- Latency: **1.07 – 2.14 s, avg 1.46 s** per structured call.
- Tokens: avg **749/call** (incl. reasoning) → paced at 6 s gaps ≈ **10 calls/min ≈ 7.5K TPM**, just inside the free-tier 8K TPM cap. No 429s in the final run (retry-on-`retry-after` backstop never fired).
- 20 calls consumed ~15K tokens of the 200K daily token budget.

## 4. Evidence
- Raw report: `scripts/spike_output/spike03_report.json` (per-call status, latency, tokens) — gitignored.
- Harness: `scripts/spike03_structured.py` (`python scripts/spike03_structured.py`, ~2.5 min; exits non-zero on transport errors).

## 5. Consequences for the plan
- **LLM-02:** `response_format: {type:"json_schema", strict:true}`, schema all-required + `additionalProperties:false`, `max_tokens ≥ 1000`.
- **LLM-03:** pacing ≈ 10 structured calls/min on free tier (TPM-bound), 429 → honor `retry-after`.
- No repair pass or model fallback needed at this stage.

## 6. Status
- ID: `SPIKE-03`
- Status: DONE
- Priority: P0
- Est: S
