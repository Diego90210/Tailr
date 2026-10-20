"""Preview image rendering: HTML replica of the CV, screenshotted by headless Chromium.

SPIKE-01 chose option A (`technical_requirements.md` §12.1): the python-docx builder
and this replica render the same content tree with the same spec, and a fidelity test
keeps them in sync (DOC-05). The screenshot is page 1 only, at the spec's page size ×96 dpi.
"""
from __future__ import annotations

import base64
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PAGE_DPI = 96
RENDER_TIMEOUT_S = 30

_WINDOWS_CHROME = (
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
)
_POSIX_CHROME = ("chromium", "chromium-browser", "google-chrome", "google-chrome-stable")


class PreviewRenderError(RuntimeError):
    """No usable browser, or the browser failed to produce a PNG."""


def find_chrome() -> str | None:
    """`CHROME_BIN` wins (deployment); otherwise probe the local Edge/Chrome/Chromium."""
    env = os.environ.get("CHROME_BIN")
    if env:
        return env if os.path.isfile(env) else None
    candidates = _WINDOWS_CHROME if sys.platform == "win32" else _POSIX_CHROME
    for candidate in candidates:
        path = candidate if os.path.isabs(candidate) else shutil.which(candidate)
        if path and os.path.isfile(path):
            return path
    return None


# ---------------------------------------------------------------- html replica

def build_html(content: dict, spec: dict, locale: str = "en") -> str:
    """Option A replica: same tree, same spec, CSS instead of python-docx."""
    m = spec["marginsIn"]
    ps = spec["pageSizeIn"]
    headings = spec["headings"][locale]
    css = f"""
@page {{ size: {ps['w']}in {ps['h']}in; margin: {m['top']}in {m['right']}in {m['bottom']}in {m['left']}in; }}
@media screen {{ body {{ padding: {m['top']}in {m['right']}in {m['bottom']}in {m['left']}in; }} }}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: {spec['font']}, serif; font-size: {spec['bodySizePt']}pt;
        line-height: {spec['lineSpacing']}; text-align: left; }}
.name {{ font-size: {spec['nameSizePt']}pt; font-weight: {'bold' if spec['nameBold'] else 'normal'}; }}
h2 {{ font-size: {spec['bodySizePt']}pt; font-weight: bold; margin-top: {spec['headingSpaceBeforePt']}pt; }}
.item {{ margin-top: {spec['itemSpaceBeforePt']}pt; }}
.row {{ display: flex; justify-content: space-between; }}
.dates {{ font-style: {'italic' if spec['dateItalic'] else 'normal'}; white-space: nowrap; }}
li {{ list-style: none; margin-top: {spec['itemSpaceBeforePt']}pt;
      padding-left: 0.25in; text-indent: -0.25in; }}
a {{ color: #{spec['linkColor']}; text-decoration: {'underline' if spec['linkUnderline'] else 'none'}; }}
"""

    def esc(s):
        return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                .replace('"', "&quot;").replace("'", "&#39;"))

    parts = [f"<!doctype html><html><head><meta charset='utf-8'><style>{css}</style></head><body>"]
    parts.append(f"<div class='name'>{esc(content['header']['name'])}</div>")
    parts.append(f"<div>{esc(content['header']['contactLine'])}</div>")
    for section in spec["sectionOrder"]:
        data = content.get(section)
        if not data:
            continue
        parts.append(f"<h2>{headings[section]}</h2>")
        if section == "summary":
            parts.append(f"<div>{esc(data)}</div>")
        elif section in ("experience", "projects"):
            for item in data:
                if section == "experience":
                    left, right = item["role"], f"{item['start']} – {item['end']}"
                else:
                    left, right = item["name"], item.get("stack", "")
                if spec["rightAlignedDates"]:
                    parts.append(f"<div class='item row'><span>{esc(left)}</span>"
                                 f"<span class='dates'>{esc(right)}</span></div>")
                else:
                    parts.append(f"<div class='item'><span>{esc(left)}</span> "
                                 f"<span class='dates'>{esc(right)}</span></div>")
                if section == "experience":
                    parts.append(f"<div>{esc(item['company'])}</div>")
                elif item.get("url"):
                    url = esc(item["url"])
                    parts.append(f"<div class='item'><a href='{url}'>{url}</a></div>")
                parts.append("<ul>")
                for b in item["bullets"]:
                    parts.append(f"<li>•&#9;&nbsp;{esc(b['text'])}</li>")
                parts.append("</ul>")
        else:
            for entry in data:
                parts.append(f"<div class='item'>{esc(entry)}</div>")
    parts.append("</body></html>")
    return "".join(parts)


# ---------------------------------------------------------------- screenshot

def render_png(content: dict, spec: dict, locale: str = "en", *,
               chrome: str | None = None) -> bytes:
    """Screenshot page 1 of the HTML replica, at the spec's page size."""
    binary = chrome or find_chrome()
    if not binary or not os.path.isfile(binary):
        raise PreviewRenderError(
            "no Chromium-family browser found; set CHROME_BIN to one "
            "(SPIKE-01 option A, technical_requirements.md §12.1)")

    width = round(spec["pageSizeIn"]["w"] * PAGE_DPI)
    height = round(spec["pageSizeIn"]["h"] * PAGE_DPI)
    with tempfile.TemporaryDirectory(prefix="tailr-preview-") as tmp:
        html = Path(tmp) / "cv.html"
        png = Path(tmp) / "preview.png"
        html.write_text(build_html(content, spec, locale), encoding="utf-8")
        result = subprocess.run(
            [binary, "--headless", "--disable-gpu", "--no-first-run", "--no-sandbox",
             "--hide-scrollbars", f"--user-data-dir={Path(tmp) / 'profile'}",
             f"--window-size={width},{height}", f"--screenshot={png}", html.as_uri()],
            capture_output=True, text=True, timeout=RENDER_TIMEOUT_S)
        if result.returncode != 0 or not png.exists():
            raise PreviewRenderError(
                f"preview render failed (exit {result.returncode}): "
                f"{result.stderr[-500:] or 'no PNG produced'}")
        data = png.read_bytes()

    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise PreviewRenderError("renderer produced a non-PNG file")
    return data


def preview_png_b64(content: dict, spec: dict, locale: str = "en", *,
                    chrome: str | None = None) -> str:
    """`preview_png_b64` field of the `/docgen` response (§12)."""
    return base64.b64encode(render_png(content, spec, locale, chrome=chrome)).decode("ascii")
