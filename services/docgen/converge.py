"""One-page convergence loop: render -> measure -> compress/enrich (§11.2, TR-FMT-1).

The loop owns the thresholds and the iteration budgets. *Which* bullets are expendable
or spare is the caller's call: docgen holds no business logic and never touches the LLM,
so both strategies arrive as callbacks that return a new content tree (or `None` when
there is nothing left to cut or add).
"""
from __future__ import annotations

from copy import deepcopy

from builder import build_docx
from measure import measure

UNDERFILL = 0.90
OVERFILL = 0.98
MAX_COMPRESS_PASSES = 3
MAX_ENRICH_PASSES = 2


def _score(metrics: dict) -> tuple[int, float]:
    """Rank attempts: one page first, then distance from the 0.90-0.98 band."""
    fill = metrics["fill_pct"]
    if fill is None:  # unmeasurable (missing font) must never win
        return (2, 0.0)
    return (0 if metrics["page_count"] == 1 else 1,
            max(0.0, UNDERFILL - fill, fill - OVERFILL))


def _attempt(content: dict, spec: dict, locale: str) -> dict:
    return {"content": content,
            "docx": build_docx(content, spec, locale),
            "metrics": measure(content, spec)}


def converge(content: dict, spec: dict, *, compress=None, enrich=None,
             locale: str = "en") -> dict:
    """Render until the tree fits one page, returning the best attempt.

    `compress(tree)` / `enrich(tree)` receive a copy and return a new tree, or `None`
    when nothing is left. Compression runs at most 3 passes (page_count > 1 or fill
    > 0.98); enrichment at most 2 (fill < 0.90 and no spare-fact callback = no loop).
    When the result still spans more than one page, `warning` is `"over_one_page"`
    instead of raising (TR-FMT-1): the caller keeps the best attempt and warns.

    Returns the winning `content`, `docx`, the measure() fields, `iterations` and
    `warning`. The caller's tree is never mutated.
    """
    current = _attempt(deepcopy(content), spec, locale)
    best = current
    iterations = compress_passes = enrich_passes = 0

    while True:
        metrics = current["metrics"]
        if metrics["fill_pct"] is None:
            break

        overfull = metrics["page_count"] > 1 or metrics["fill_pct"] > OVERFILL
        if not overfull and metrics["fill_pct"] >= UNDERFILL:
            break

        if overfull:
            if compress is None or compress_passes >= MAX_COMPRESS_PASSES:
                break
            compress_passes += 1
            next_content = compress(deepcopy(current["content"]))
        else:
            if enrich is None or enrich_passes >= MAX_ENRICH_PASSES:
                break
            enrich_passes += 1
            next_content = enrich(deepcopy(current["content"]))

        if next_content is None:
            break
        iterations += 1
        current = _attempt(next_content, spec, locale)
        if _score(current["metrics"]) < _score(best["metrics"]):
            best = current

    metrics = best["metrics"]
    return {"content": best["content"], "docx": best["docx"], **metrics,
            "iterations": iterations,
            "warning": "over_one_page" if (metrics["page_count"] or 0) > 1 else None}
