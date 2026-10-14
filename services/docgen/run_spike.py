"""SPIKE-01 runner: render every fixture three ways and compare.

  docx  -> Word COM (oracle)      -> word.pdf
  docx  -> LibreOffice container  -> lo.pdf  (+ png via Draw)
  html  -> Edge headless          -> edge.pdf (+ png screenshot)

Compare: page_count, normalized line breaks, fill_pct (from PDF text coords).

Usage:
  python run_spike.py            # full render + compare + report
  python run_spike.py --compare  # reuse existing PDFs (fast iteration)
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import time
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

import cvdoc

HERE = Path(__file__).resolve().parent
OUT = HERE / "spike_output"
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
LO_IMAGE = "linuxserver/libreoffice:latest"
USABLE_H_PT = (cvdoc.DEFAULT_FORMAT_SPEC["pageSizeIn"]["h"]
               - cvdoc.DEFAULT_FORMAT_SPEC["marginsIn"]["top"]
               - cvdoc.DEFAULT_FORMAT_SPEC["marginsIn"]["bottom"]) * 72


# ---------------------------------------------------------------- renderers

def render_docs() -> None:
    OUT.mkdir(exist_ok=True)
    for name in cvdoc.FIXTURES:
        content = cvdoc.fixture_content(name)
        cvdoc.build_docx(content, cvdoc.DEFAULT_FORMAT_SPEC).save(OUT / f"{name}.docx")
        (OUT / f"{name}.html").write_text(
            cvdoc.build_html(content, cvdoc.DEFAULT_FORMAT_SPEC), encoding="utf-8")


def render_word(names: list[str]) -> None:
    """One Word process per file (COM automation is stateful; keep it dumb)."""
    for n in names:
        subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
             str(HERE / "word_export.ps1"), "-Docx", str(OUT / f"{n}.docx"),
             "-Pdf", str(OUT / f"{n}.word.pdf"), "-StatsJson", str(OUT / f"{n}.word.json")],
            check=True, capture_output=True, timeout=120)


def render_edge(names: list[str]) -> None:
    import shutil
    # ponytail: a persistent profile serves stale file:// copies; wipe it every run
    shutil.rmtree(OUT / "edge_profile", ignore_errors=True)
    for n in names:
        html = (OUT / f"{n}.html").resolve()
        pdf = OUT / f"{n}.edge.pdf"
        png = OUT / f"{n}.edge.png"
        base = [EDGE, "--headless", "--disable-gpu", "--no-first-run", "--no-sandbox",
                f"--user-data-dir={OUT / 'edge_profile'}"]
        subprocess.run(base + [f"--no-pdf-header-footer", f"--print-to-pdf={pdf}",
                               html.as_uri()],
                       check=True, capture_output=True, timeout=60)
        subprocess.run(base + ["--hide-scrollbars", "--window-size=816,1056",
                               f"--screenshot={png}", html.as_uri()],
                       check=True, capture_output=True, timeout=60)


def render_libreoffice(names: list[str]) -> None:
    """One container: all docx -> pdf, then all pdf -> png (page 1 preview)."""
    def run(args: list[str]) -> None:
        r = subprocess.run(["docker", "run", "--rm", "-v", f"{OUT}:/data",
                            "--entrypoint", "soffice", LO_IMAGE] + args,
                           capture_output=True, text=True, timeout=600)
        if r.returncode != 0:
            raise RuntimeError(f"libreoffice failed: {r.stderr[-800:]}")

    common = ["--headless", "--norestore", "--nofirststartwizard"]
    for n in names:
        run(common + ["--convert-to", "pdf", "--outdir", "/data",
                      f"/data/{n}.docx"])
        # soffice names the output after the input basename -> rename to .lo.pdf
        produced, final = OUT / f"{n}.pdf", OUT / f"{n}.lo.pdf"
        if not produced.exists():
            raise RuntimeError(f"libreoffice produced no pdf for {n}")
        produced.replace(final)
    for n in names:
        run(common + ["--convert-to", "png", "--outdir", "/data",
                      f"/data/{n}.lo.pdf"])


# ---------------------------------------------------------------- pdf stats

def _norm(line: str) -> str:
    # PDFs disagree on codepoints, not content: decomposed accents (i + U+0301) and
    # dotless-i glyph mapping from Chromium font subsets. Fold to ASCII-ish before diffing.
    s = unicodedata.normalize("NFD", line)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.replace("ı", "i")
    return re.sub(r"\s+", " ", s).strip()


def pdf_stats(path: Path) -> dict:
    from pypdf import PdfReader
    reader = PdfReader(str(path))
    ys: list[float] = []
    lines: list[str] = []
    for page in reader.pages:
        page_ys: list[float] = []

        def visitor(text, cm, tm, fd, fs, page_ys=page_ys):
            if text.strip():
                # baseline y composed with the CTM: y' = b*x + d*y + f
                page_ys.append(cm[1] * tm[4] + cm[3] * tm[5] + cm[5])

        text = page.extract_text(visitor_text=visitor) or ""
        lines += [_norm(l) for l in text.splitlines() if _norm(l)]
        ys.append(page_ys)
    # fill_pct = how full page 1 is (multi-page fill is meaningless for comparison)
    p1 = ys[0] if ys else []
    fill = (max(p1) - min(p1)) / USABLE_H_PT if p1 else None
    return {"pages": len(reader.pages), "lines": len(lines),
            "line_list": lines, "fill_pct": round(fill, 4) if fill else None}


def line_match(a: list[str], b: list[str]) -> float:
    return round(SequenceMatcher(None, a, b).ratio(), 4)


# ---------------------------------------------------------------- report

def word_stats(name: str) -> dict:
    return json.loads((OUT / f"{name}.word.json").read_text(encoding="utf-8-sig"))


def build_report() -> tuple[str, list[dict]]:
    rows, sections = [], []
    for name in cvdoc.FIXTURES:
        content = cvdoc.fixture_content(name)
        measured = cvdoc.measure(content, cvdoc.DEFAULT_FORMAT_SPEC)
        w_json = word_stats(name)
        w = pdf_stats(OUT / f"{name}.word.pdf")
        lo = pdf_stats(OUT / f"{name}.lo.pdf")
        ed = pdf_stats(OUT / f"{name}.edge.pdf")
        row = {
            "fixture": name,
            "measure_fill": measured["fill_pct"],
            "measure_lines": measured["line_count"],
            "word_pages": w_json["pages"], "word_lines": w_json["lines"],
            "word_fill": w["fill_pct"],
            "lo_pages": lo["pages"], "lo_lines": len(lo["line_list"]),
            "lo_fill": lo["fill_pct"],
            "edge_pages": ed["pages"], "edge_lines": len(ed["line_list"]),
            "edge_fill": ed["fill_pct"],
            "match_word_lo": line_match(w["line_list"], lo["line_list"]),
            "match_word_edge": line_match(w["line_list"], ed["line_list"]),
            "pages_word_edge_ok": w_json["pages"] == ed["pages"],
            "pages_word_lo_ok": w_json["pages"] == lo["pages"],
        }
        rows.append(row)
        sections.append(row)

    hdr = ("| fixture | measure fill | Word pg/ln/fill | LO pg/ln/fill | Edge pg/ln/fill "
           "| lines W~LO | lines W~Edge |\n|---|---|---|---|---|---|---|")
    body = [
        f"| {r['fixture']} | {r['measure_fill']} | {r['word_pages']}/{r['word_lines']}/{r['word_fill']} "
        f"| {r['lo_pages']}/{r['lo_lines']}/{r['lo_fill']} "
        f"| {r['edge_pages']}/{r['edge_lines']}/{r['edge_fill']} "
        f"| {r['match_word_lo']} | {r['match_word_edge']} |"
        for r in rows
    ]
    md = ["# SPIKE-01 comparison", "", hdr, *body, ""]
    md.append(f"- Word/Edge page_count equal on all fixtures: "
              f"**{all(r['pages_word_edge_ok'] for r in rows)}**")
    md.append(f"- Word/LO page_count equal on all fixtures: "
              f"**{all(r['pages_word_lo_ok'] for r in rows)}**")
    md.append(f"- mean line match W~Edge: "
              f"{round(sum(r['match_word_edge'] for r in rows) / len(rows), 4)}")
    md.append(f"- mean line match W~LO:   "
              f"{round(sum(r['match_word_lo'] for r in rows) / len(rows), 4)}")
    md.append("")
    (OUT / "report.md").write_text("\n".join(md), encoding="utf-8")
    (OUT / "report.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    return "\n".join(md), rows


def main() -> int:
    only_compare = "--compare" in sys.argv
    names = list(cvdoc.FIXTURES)
    t0 = time.time()
    if not only_compare:
        print("render docs...", flush=True)
        render_docs()
        print("word...", flush=True)
        render_word(names)
        print("edge...", flush=True)
        render_edge(names)
        print("libreoffice container...", flush=True)
        render_libreoffice(names)
    md, _ = build_report()
    print(md)
    print(f"done in {round(time.time() - t0, 1)}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
