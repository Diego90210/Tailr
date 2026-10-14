"""DOC-02 acceptance: pagination measurement with real font metrics (§11.2, TR-FMT-2).

Oracle-gated tests need `spike_output/*.word.pdf` (produced by `python run_spike.py`);
without them only the deterministic parts run.
"""
from __future__ import annotations

import math
from pathlib import Path

import pytest

import cvdoc
import measure as measure_mod
from format_specs import DEFAULT_FORMAT_SPEC

FIXTURES = list(cvdoc.FIXTURES)

# Calibrated against the SPIKE-01 Word oracle (fixtures 01/02/05, ratio 0.93).
# Pinned so a spec/corpus change that silently moves fill has to be acknowledged.
GOLDEN = {
    "01_junior_short": (0.4518, 20, 1),
    "02_mid_standard": (0.7681, 34, 1),
    "03_senior_full": (1.0645, 48, 2),
    "04_staff_overfull": (1.4306, 65, 2),
    "05_latam_es_ats": (0.8349, 38, 1),
}

OUT = Path(__file__).resolve().parents[1] / "spike_output"
_have_oracle = all((OUT / f"{n}.word.pdf").exists() for n in FIXTURES)

oracle = pytest.mark.skipif(
    not _have_oracle, reason="spike artifacts missing — run: python run_spike.py")


def test_measure_returns_fill_line_count_and_page_count():
    m = measure_mod.measure(cvdoc.fixture_content("01_junior_short"), DEFAULT_FORMAT_SPEC)
    assert m["missing_fonts"] == []
    assert 0 < m["fill_pct"] < 1
    assert m["line_count"] == 20
    assert m["page_count"] == 1


def test_measure_reports_missing_font_without_substituting(monkeypatch):
    monkeypatch.setattr(measure_mod, "FONT_FILE", "definitely-not-a-font.ttc")
    m = measure_mod.measure(cvdoc.fixture_content("01_junior_short"), DEFAULT_FORMAT_SPEC)
    assert m["missing_fonts"] == [DEFAULT_FORMAT_SPEC["font"]]
    assert m["fill_pct"] is None and m["line_count"] is None and m["page_count"] is None


def test_measure_grows_with_added_content():
    content = cvdoc.fixture_content("01_junior_short")
    before = measure_mod.measure(content, DEFAULT_FORMAT_SPEC)
    content["experience"][0]["bullets"].append(
        {"text": "Extra achievement " * 12, "factIds": ["fx"]})
    after = measure_mod.measure(content, DEFAULT_FORMAT_SPEC)
    assert after["line_count"] > before["line_count"]
    assert after["fill_pct"] > before["fill_pct"]


def test_measure_is_deterministic():
    a = measure_mod.measure(cvdoc.fixture_content("03_senior_full"), DEFAULT_FORMAT_SPEC)
    b = measure_mod.measure(cvdoc.fixture_content("03_senior_full"), DEFAULT_FORMAT_SPEC)
    assert a == b


def test_measure_page_count_is_ceil_of_fill():
    for name in FIXTURES:
        m = measure_mod.measure(cvdoc.fixture_content(name), DEFAULT_FORMAT_SPEC)
        assert m["page_count"] == max(1, math.ceil(m["fill_pct"])), name


def test_calibrated_fill_matches_recorded_corpus():
    for name, expected in GOLDEN.items():
        m = measure_mod.measure(cvdoc.fixture_content(name), DEFAULT_FORMAT_SPEC)
        assert m == {"fill_pct": expected[0], "line_count": expected[1],
                     "page_count": expected[2], "missing_fonts": []}, name


def test_count_wrapped_lines_splits_on_width():
    font, scale = measure_mod.load_font(DEFAULT_FORMAT_SPEC["bodySizePt"])
    assert font is not None
    assert measure_mod.count_wrapped_lines("", font, scale, 400) == 1
    assert measure_mod.count_wrapped_lines("short line", font, scale, 400) == 1
    long_text = " ".join(["word"] * 200)
    assert measure_mod.count_wrapped_lines(long_text, font, scale, 400) > 1


@oracle
def test_calibrated_fill_tracks_word_rendering():
    """Calibrated fill must stay within the SPIKE-01 tolerance (0.04) of Word's content box."""
    import pypdf
    usable_h = (DEFAULT_FORMAT_SPEC["pageSizeIn"]["h"]
                - DEFAULT_FORMAT_SPEC["marginsIn"]["top"]
                - DEFAULT_FORMAT_SPEC["marginsIn"]["bottom"]) * 72
    for name in FIXTURES:
        if GOLDEN[name][2] != 1:
            continue  # an overflowing fixture renders 2 pages; no single page to compare
        reader = pypdf.PdfReader(str(OUT / f"{name}.word.pdf"))
        ys: list[float] = []

        def visitor(text, cm, tm, fd, fs, ys=ys):
            if text.strip():
                ys.append(cm[1] * tm[4] + cm[3] * tm[5] + cm[5])

        reader.pages[0].extract_text(visitor_text=visitor)
        # content box = baseline span + first ascent (15pt name) + last descent (11pt body)
        box = (max(ys) - min(ys)) + 14.25 + 2.5
        fill = measure_mod.measure(cvdoc.fixture_content(name), DEFAULT_FORMAT_SPEC)["fill_pct"]
        assert abs(fill - box / usable_h) <= 0.04, f"{name}: {fill} vs {box / usable_h}"
