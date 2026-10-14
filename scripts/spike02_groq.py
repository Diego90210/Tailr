"""SPIKE-02: validate Groq as primary LLM provider.

Measures real rate limits (RPM/TPM headers + burst behavior) and checks
JSON-schema structured output reliability on the target model.

Usage: python scripts/spike02_groq.py
Report: scripts/spike_output/spike02_report.json
"""

import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests
from pydantic import BaseModel, ValidationError

API = "https://api.groq.com/openai/v1"
MODEL = "openai/gpt-oss-120b"  # free tier: 30 RPM / 1K RPD / 8K TPM, strict structured output
OUT = Path(__file__).resolve().parent / "spike_output"

RATE_HEADERS = [
    "x-ratelimit-limit-requests",
    "x-ratelimit-limit-tokens",
    "x-ratelimit-remaining-requests",
    "x-ratelimit-remaining-tokens",
    "x-ratelimit-reset-tokens",
    "retry-after",
]


def api_key() -> str:
    for line in Path(__file__).resolve().parents[1].joinpath(".env").read_text().splitlines():
        if line.startswith("GROQ_API_KEY="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("GROQ_API_KEY missing from .env")


KEY = api_key()
HEADERS = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}


def chat(messages, response_format=None, max_tokens=64, timeout=60):
    body = {"model": MODEL, "messages": messages, "max_tokens": max_tokens, "temperature": 0}
    if response_format:
        body["response_format"] = response_format
    t0 = time.perf_counter()
    r = requests.post(f"{API}/chat/completions", headers=HEADERS, json=body, timeout=timeout)
    latency = time.perf_counter() - t0
    meta = {h: r.headers.get(h) for h in RATE_HEADERS if r.headers.get(h) is not None}
    return r, meta, latency


def probe():
    """One plain call: confirms key + captures advertised limits from headers."""
    r, meta, latency = chat([{"role": "user", "content": "Reply with the word ok."}])
    models = requests.get(f"{API}/models", headers=HEADERS, timeout=30)
    return {
        "status": r.status_code,
        "latency_s": round(latency, 3),
        "rate_headers": meta,
        "models_available": models.status_code == 200,
        "model_in_list": models.status_code == 200
        and any(m.get("id") == MODEL for m in models.json().get("data", [])),
    }


def burst(n=40, workers=8):
    """Fire n tiny requests as fast as possible; expect 429 at the RPM ceiling."""
    def one(_):
        r, meta, latency = chat([{"role": "user", "content": "Reply with the word ok."}])
        return {
            "status": r.status_code,
            "latency_s": round(latency, 3),
            "retry_after": r.headers.get("retry-after"),
            "error": None if r.status_code == 200 else r.text[:200],
            "meta": meta,
        }

    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as ex:
        results = list(ex.map(one, range(n)))
    elapsed = time.perf_counter() - t0
    ok = [x for x in results if x["status"] == 200]
    limited = [x for x in results if x["status"] == 429]
    other = [x for x in results if x["status"] not in (200, 429)]
    return {
        "sent": n,
        "workers": workers,
        "elapsed_s": round(elapsed, 2),
        "ok": len(ok),
        "http_429": len(limited),
        "other_errors": len(other),
        "observed_rpm": round(len(ok) / elapsed * 60) if elapsed else None,
        "first_429_retry_after_s": next((x["retry_after"] for x in limited), None),
        "sample_rate_headers": (limited or ok or results)[0]["meta"],
        "other_error_sample": other[0]["error"] if other else None,
    }


# strict mode: every field required, additionalProperties false (Groq requirement)
JD_SCHEMA = {
    "type": "object",
    "properties": {
        "role_title": {"type": "string"},
        "seniority": {"type": "string", "enum": ["junior", "mid", "senior", "lead"]},
        "language": {"type": "string", "enum": ["es", "en"]},
        "must_have": {"type": "array", "items": {"type": "string"}},
        "nice_to_have": {"type": "array", "items": {"type": "string"}},
        "red_flags": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["role_title", "seniority", "language", "must_have", "nice_to_have", "red_flags"],
    "additionalProperties": False,
}


class JDAnalysis(BaseModel):
    role_title: str
    seniority: str
    language: str
    must_have: list[str]
    nice_to_have: list[str]
    red_flags: list[str]


POSTING = """We are hiring a Senior Frontend Engineer in Madrid (hybrid).
Must: 5+ years TypeScript, React, Next.js, testing with Vitest, CI/CD with GitHub Actions.
Nice: i18n with next-intl, Tailwind, accessibility (WCAG), Spanish and English.
Not a fit: no production experience, unwilling to work hybrid 3 days/week."""


def structured(n=5):
    """n strict-mode calls; validate with pydantic. Full 20-prompt run lives in SPIKE-03."""
    rf = {
        "type": "json_schema",
        "json_schema": {"name": "jd_analysis", "strict": True, "schema": JD_SCHEMA},
    }
    rows, failures = [], 0
    for i in range(n):
        r, meta, latency = chat(
            [
                {"role": "system", "content": "You extract job-posting analysis data."},
                {"role": "user", "content": POSTING},
            ],
            response_format=rf,
            max_tokens=400,
        )
        row = {"i": i, "status": r.status_code, "latency_s": round(latency, 3)}
        if r.status_code != 200:
            row["error"] = r.text[:200]
            failures += 1
        else:
            content = r.json()["choices"][0]["message"]["content"]
            try:
                JDAnalysis.model_validate_json(content)
                row["valid"] = True
            except ValidationError as e:
                row["valid"] = False
                row["error"] = str(e)[:300]
                failures += 1
            row["usage"] = r.json().get("usage", {})
        rows.append(row)
        time.sleep(0.5)  # stay inside the free-tier RPM
    return {"calls": n, "failures": failures, "failure_rate": failures / n, "rows": rows}


def main():
    probe_result = probe()
    struct_result = structured()
    print("waiting 65s for the per-minute window to clear before the burst ...")
    time.sleep(65)
    report = {
        "model": MODEL,
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "probe": probe_result,
        "structured_output": struct_result,
        "burst": burst(),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "spike02_report.json"
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(json.dumps({k: v for k, v in report.items() if k != "structured_output"}, indent=2))
    print(json.dumps(report["structured_output"], indent=2))
    print(f"report -> {path}")
    # ponytail: the live run IS the check — fail loudly if the spike's core claims broke
    assert probe_result["status"] == 200, "probe call failed"
    assert struct_result["failures"] == 0, f"structured output failures: {struct_result['failures']}"


if __name__ == "__main__":
    main()
