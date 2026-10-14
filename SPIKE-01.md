# SPIKE-01: One-page fidelity rendering

## 1. Objective
Prove that the generation engine can render a faithful CV content tree to `.docx` and produce a preview image that matches the document's pagination.

## 2. Methodology
1.  **Rendering:** Use `python-docx` to generate a `.docx` file from a sample data corpus.
2.  **Preview:** Implement two preview methods:
    *   **A (HTML/Browser):** Replicate the doc structure in React/HTML/Tailwind and use `html2canvas` or similar.
    *   **B (LibreOffice):** Invoke LibreOffice in headless mode to convert the generated `.docx` to a PDF/PNG.
3.  **Comparison:** Compare the two results against the `docx` document:
    *   Does the page count match?
    *   Do the line breaks and content mapping (fill_pct) remain consistent?
4.  **Selection:** Based on fidelity and complexity, choose the production approach (Option A vs B) and document the decision.

## 3. Scope
- Test against 5 real profiles of varying length.
- Focus: Font metric consistency, margins, and section spacing.

## 4. Result (2026-10-07)

Corpus: 5 fixture content trees (`services/docgen/cvdoc.py`), rendered three ways:

| path | tool |
|---|---|
| oracle | Word COM → `*.word.pdf` + page/line stats |
| A | HTML replica → Edge headless (`--print-to-pdf`, `--screenshot`) |
| B | `linuxserver/libreoffice` container → `*.lo.pdf` → PNG via Draw |

Raw table: `services/docgen/spike_output/report.md` (reproduce: `python run_spike.py`).

### Findings

| metric | A (Chromium) | B (LibreOffice container) |
|---|---|---|
| `page_count` vs Word | **5/5 equal** | 5/5 equal |
| `line_count` vs Word | **5/5 equal** (20/34/48/65/38) | 3/5 (03, 04 off by +2 lines) |
| mean line-break match vs Word | **0.967** | 0.843 |
| `fill_pct` delta vs Word | ≤ 0.04 | up to +0.12 |
| font actually used | Cambria (correct) | **NotoSerif (substituted — Cambria absent)** |
| preview PNG | screenshot + screen-media margin CSS | Draw export of PDF |
| cost | ~1.4 s/artifact, one deploy target | 3.73 GB image, ~10 s/artifact, second host |

- Residual A mismatches are **1-word wrap positions** on 4 of 205 lines; page and line counts unaffected.
- `measure()` (Pillow, TR-FMT-2) reproduces Word's `line_count` **5/5** and `page_count` **5/5**, but `fill_pct` runs ~+0.05…0.09 high → calibrate line height against the Word oracle in DOC-02.
- Known artifact: Chromium PDF subsets map `í` to `ı`+combining accent; line-diff must fold Unicode (NFC/strip marks) before comparing — `run_spike._norm` does.
- Screenshot PNGs need `@media screen { body { padding: <margins> } }` — `@page` applies only to print/PDF. Edge profile dir must be wiped per run (stale `file://` cache).

### Decision: **Option A** (HTML replica + headless Chromium)

A matches Word's pagination exactly on the corpus while B — without proprietary Cambria, which cannot ship in the container — already diverges in line breaks and fill. A also avoids the second deploy target. Confirms the recommendation in `technical_requirements.md` §12.1; the `/docgen` contract (`preview_png_b64`) stays fixed, so B remains a hosting decision later.

Follow-ups (feature ids): DOC-04 (PNG via print-to-PDF rasterization or screen-margin screenshot), DOC-05 (fidelity test must Unicode-fold line diffs), DOC-02 (calibrate `measure()` fill), DOC-01 (builder keeps docx↔HTML 1:1).

## 5. Status
- ID: `SPIKE-01`
- Status: **DONE** (2026-10-07)
- Evidence: `services/docgen/tests/test_spike01.py` — 7 passed; `./init.sh` — `[OK] Environment ready`
