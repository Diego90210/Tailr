"""Pagination measurement with real font metrics (technical_requirements.md §11.2, TR-FMT-2).

Deterministic: the same content tree and spec always yield the same numbers (TR-FMT-4).
A missing font is reported, never substituted (TR-FMT-5). Pure function of the content
tree, the spec and the font file — no rendering, no network.
"""
from __future__ import annotations

import math

from PIL import ImageFont

FONT_FILE = "cambria.ttc"  # Windows; TR-FMT-5: report missing fonts, never substitute
SCALE = 4  # load at 4x pt and divide widths — sub-pixel wrap accuracy without a HiDPI API

# Calibrated so `fill_pct` reflects real page occupancy, not the line-box sum.
# The §11.2 sum over-counts space_before/heading gaps ~6-8% vs Word (SPIKE-01 oracle,
# single-page fixtures: raw 0.486/0.826/0.898 -> rendered content box 0.455/0.769/0.828,
# mean ratio 0.93). Without it the DOC-03 loop would compress/fill against an inflated
# number and leave the page under 92% full (RF-14.2).
FILL_CALIBRATION = 0.93


def load_font(size_pt: float, scale: int = SCALE):
    """Return `(font, scale)` for the spec font at `size_pt`, or `(None, scale)` if absent."""
    try:
        return ImageFont.truetype(FONT_FILE, int(round(size_pt * scale)), index=0), scale
    except OSError:
        return None, scale


def count_wrapped_lines(text: str, font, scale: int, width_pt: float) -> int:
    """Greedy word wrap: how many lines `text` occupies at `width_pt` (min 1)."""
    words = text.split()
    if not words:
        return 1
    lines, cur = 1, ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if font.getlength(trial) / scale <= width_pt:
            cur = trial
        else:
            lines += 1
            cur = w
    return lines


def line_height(font, scale: int, line_spacing: float) -> float:
    """One text line's height in points: (ascent + descent) x line spacing."""
    ascent, descent = font.getmetrics()
    return (ascent + descent) / scale * line_spacing


def measure(content: dict, spec: dict) -> dict:
    """Content height / usable height, plus line and page counts (TR-FMT-2).

    Every section heading is one line; heading text is never wrapped (it is short).
    Returns `missing_fonts` non-empty with null metrics when the font file is absent.
    """
    m = spec["marginsIn"]
    ps = spec["pageSizeIn"]
    usable_w = (ps["w"] - m["left"] - m["right"]) * 72
    usable_h = (ps["h"] - m["top"] - m["bottom"]) * 72

    font, scale = load_font(spec["bodySizePt"])
    if font is None:
        return {"fill_pct": None, "line_count": None, "page_count": None,
                "missing_fonts": [spec["font"]]}
    lh = line_height(font, scale, spec["lineSpacing"])
    total_pt, line_count = 0.0, 0

    def add_lines(text: str, width_pt: float, before: float = 0.0) -> None:
        nonlocal total_pt, line_count
        n = count_wrapped_lines(text, font, scale, width_pt)
        total_pt += before + n * lh
        line_count += n

    add_lines("", usable_w)  # name
    add_lines("", usable_w)  # contact line
    for section in spec["sectionOrder"]:
        data = content.get(section)
        if not data:
            continue
        add_lines("", usable_w, spec["headingSpaceBeforePt"])
        if section == "summary":
            add_lines(data, usable_w)
        elif section in ("experience", "projects"):
            for item in data:
                left = item["role"] if section == "experience" else item["name"]
                add_lines(left, usable_w, spec["itemSpaceBeforePt"])
                if section == "experience":
                    add_lines("", usable_w)  # company line
                elif item.get("url"):
                    add_lines("", usable_w, spec["itemSpaceBeforePt"])
                for b in item["bullets"]:
                    add_lines(b["text"], usable_w - 18, spec["itemSpaceBeforePt"])
        else:
            for entry in data:
                add_lines(entry, usable_w, spec["itemSpaceBeforePt"])

    fill = total_pt / usable_h * FILL_CALIBRATION
    return {"fill_pct": round(fill, 4), "line_count": line_count,
            "page_count": max(1, math.ceil(fill)), "missing_fonts": []}
