"""DOC-03 acceptance: one-page convergence loop (§11.2, TR-FMT-1)."""
from __future__ import annotations

import cvdoc
import measure as measure_mod
from builder import build_docx
from converge import converge
from format_specs import DEFAULT_FORMAT_SPEC as SPEC


def _fills_to_band(content: dict) -> dict:
    """Grow a fixture until it sits in 0.90-0.98, so no callback is needed."""
    while measure_mod.measure(content, SPEC)["fill_pct"] < 0.92:
        content["experience"][1]["bullets"].append({"text": "Line", "factIds": ["fx"]})
    return content


def _compress_oldest(content: dict):
    roles = content["experience"]
    oldest = roles[-1]
    if len(roles) > 2:
        roles.pop()
    elif oldest["bullets"]:
        oldest["bullets"].pop()
    else:
        return None
    return content


def _enrich(content: dict):
    content["experience"][0]["bullets"].append(
        {"text": "Extra achievement for the page.", "factIds": ["fx"]})
    return content


def test_returns_untouched_content_when_it_already_fits():
    content = _fills_to_band(cvdoc.fixture_content("02_mid_standard"))
    before = measure_mod.measure(content, SPEC)
    calls = []

    result = converge(content, SPEC,
                      compress=lambda c: calls.append("compress"),
                      enrich=lambda c: calls.append("enrich"))

    assert calls == []
    assert result["iterations"] == 0
    assert result["warning"] is None
    assert result["page_count"] == 1
    assert result["fill_pct"] == before["fill_pct"]


def test_compresses_overfull_content_to_one_page():
    content = cvdoc.fixture_content("03_senior_full")
    result = converge(content, SPEC, compress=_compress_oldest)

    assert result["page_count"] == 1
    assert 0.90 <= result["fill_pct"] <= 0.98
    assert result["iterations"] == 2
    assert result["warning"] is None
    assert len(result["content"]["experience"]) == 2  # the oldest role was dropped
    assert [p.text for p in result["docx"].paragraphs] == [
        p.text for p in build_docx(result["content"], SPEC).paragraphs]


def test_stops_after_max_compression_passes_and_warns_on_overflow():
    content = cvdoc.fixture_content("04_staff_overfull")

    result = converge(content, SPEC, compress=lambda c: c)

    assert result["iterations"] == 3
    assert result["page_count"] == 2
    assert result["warning"] == "over_one_page"
    assert result["content"] == content


def test_returns_best_compression_attempt_when_it_overshoots():
    content = cvdoc.fixture_content("03_senior_full")

    result = converge(content, SPEC, compress=lambda c: c["experience"].pop() and c)

    assert result["iterations"] == 2
    assert result["page_count"] == 1
    assert result["fill_pct"] == 0.9804  # closer to the band than the last, underfilled attempt
    assert len(result["content"]["experience"]) == 2


def test_stops_when_caller_has_nothing_left_to_cut():
    result = converge(cvdoc.fixture_content("03_senior_full"), SPEC,
                      compress=lambda c: None)

    assert result["iterations"] == 0
    assert result["page_count"] == 2
    assert result["warning"] == "over_one_page"


def test_enriches_underfilled_content_and_stops_after_max_passes():
    content = cvdoc.fixture_content("01_junior_short")
    before = measure_mod.measure(content, SPEC)
    calls = []

    def enrich(tree):
        calls.append(tree)
        return _enrich(tree)

    result = converge(content, SPEC, enrich=enrich)

    assert len(calls) == 2
    assert result["iterations"] == 2
    assert result["page_count"] == 1
    assert result["fill_pct"] > before["fill_pct"]
    assert result["fill_pct"] == measure_mod.measure(result["content"], SPEC)["fill_pct"]
    assert result["warning"] is None


def test_underfill_without_spare_facts_returns_as_is():
    content = cvdoc.fixture_content("01_junior_short")

    result = converge(content, SPEC)

    assert result["iterations"] == 0
    assert result["fill_pct"] == measure_mod.measure(content, SPEC)["fill_pct"]
    assert result["warning"] is None


def test_missing_font_stops_the_loop_and_reports_the_font(monkeypatch):
    monkeypatch.setattr(measure_mod, "FONT_FILE", "definitely-not-a-font.ttc")
    calls = []

    result = converge(cvdoc.fixture_content("04_staff_overfull"), SPEC,
                      compress=lambda c: calls.append("compress"))

    assert calls == []
    assert result["iterations"] == 0
    assert result["missing_fonts"] == [SPEC["font"]]
    assert result["fill_pct"] is None and result["warning"] is None


def test_does_not_mutate_the_callers_content():
    content = cvdoc.fixture_content("03_senior_full")

    converge(content, SPEC, compress=_compress_oldest)

    assert content == cvdoc.fixture_content("03_senior_full")
