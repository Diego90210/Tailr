"""SPIKE-01 acceptance: same content tree through docx (Word) vs HTML (Edge) vs
LibreOffice container must agree on page count and line breaks.

Oracle artifacts (spike_output/*.pdf) are produced by `python run_spike.py`;
without them only the deterministic parts (builder + measure) are checked.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import cvdoc
import run_spike

OUT = run_spike.OUT
NAMES = list(cvdoc.FIXTURES)


def _has_oracle() -> bool:
    return all((OUT / f"{n}.word.pdf").exists() and (OUT / f"{n}.edge.pdf").exists()
               for n in NAMES)


oracle = pytest.mark.skipif(
    not _has_oracle(), reason="spike artifacts missing — run: python run_spike.py")


def test_measure_fills_are_sane():
    """Pillow metrics (TR-FMT-2): every fixture measures and stays within bounds."""
    for name in NAMES:
        m = cvdoc.measure(cvdoc.fixture_content(name), cvdoc.DEFAULT_FORMAT_SPEC)
        assert m["missing_fonts"] == []
        assert m["fill_pct"] is not None and 0 < m["fill_pct"] < 3
        assert m["line_count"] > 0 and m["page_count"] >= 1


def test_measure_line_count_matches_word_oracle():
    """measure() must reproduce Word's line count on the whole fixture corpus."""
    if not _has_oracle():
        pytest.skip("spike artifacts missing — run: python run_spike.py")
    for name in NAMES:
        word = json.loads((OUT / f"{name}.word.json").read_text(encoding="utf-8-sig"))
        m = cvdoc.measure(cvdoc.fixture_content(name), cvdoc.DEFAULT_FORMAT_SPEC)
        assert m["line_count"] == word["lines"], f"{name}: measure vs Word"


@oracle
def test_page_count_word_equals_edge():
    """Option A (HTML replica): pagination must match the Word oracle on every fixture."""
    for name in NAMES:
        word = json.loads((OUT / f"{name}.word.json").read_text(encoding="utf-8-sig"))
        edge = run_spike.pdf_stats(OUT / f"{name}.edge.pdf")
        assert word["pages"] == edge["pages"], f"{name}: word={word['pages']} edge={edge['pages']}"


@oracle
def test_line_count_word_equals_edge():
    for name in NAMES:
        word = json.loads((OUT / f"{name}.word.json").read_text(encoding="utf-8-sig"))
        edge = run_spike.pdf_stats(OUT / f"{name}.edge.pdf")
        assert word["lines"] == edge["lines"], f"{name}: word={word['lines']} edge={edge['lines']}"


@oracle
def test_line_break_fidelity_edge():
    """Line-break match vs Word ≥ 0.90 per fixture (spike decision threshold)."""
    for name in NAMES:
        w = run_spike.pdf_stats(OUT / f"{name}.word.pdf")
        e = run_spike.pdf_stats(OUT / f"{name}.edge.pdf")
        match = run_spike.line_match(w["line_list"], e["line_list"])
        assert match >= 0.90, f"{name}: W~Edge line match {match} < 0.90"


@oracle
def test_lo_container_line_count_differs_without_cambria():
    """Documents the option-B finding: container substitutes NotoSerif for Cambria,
    so LO line counts diverge from Word on the dense fixtures."""
    diverging = 0
    for name in NAMES:
        word = json.loads((OUT / f"{name}.word.json").read_text(encoding="utf-8-sig"))
        lo = run_spike.pdf_stats(OUT / f"{name}.lo.pdf")
        if word["lines"] != lo["lines"]:
            diverging += 1
    assert diverging >= 1, "expected at least one LO divergence (font substitution)"


@oracle
def test_preview_pngs_exist_for_both_options():
    for name in NAMES:
        assert (OUT / f"{name}.edge.png").stat().st_size > 5000
        assert (OUT / f"{name}.lo.png").stat().st_size > 5000
