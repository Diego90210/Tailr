"""DOC-04 acceptance: HTML replica -> headless-Chromium PNG, `preview_png_b64` (§12.1, RF-5.6)."""
from __future__ import annotations

import base64
import io
from copy import deepcopy

import pytest
from PIL import Image

import cvdoc
import preview
from format_specs import DEFAULT_FORMAT_SPEC as SPEC

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
browser = pytest.mark.skipif(preview.find_chrome() is None,
                             reason="no Chromium-family browser (set CHROME_BIN)")


def _content(name: str = "02_mid_standard") -> dict:
    return cvdoc.fixture_content(name)


def test_html_replica_follows_the_requested_locale():
    html = preview.build_html(_content(), SPEC, "es")

    assert "PERFIL PROFESIONAL" in html and "EXPERIENCIA" in html
    assert "PROFESSIONAL PROFILE" not in html and "EXPERIENCE" not in html


def test_html_replica_escapes_content_instead_of_executing_it():
    content = _content("02_mid_standard")
    content["header"]["name"] = "<script>alert(1)</script>"
    content["experience"][0]["bullets"][0]["text"] = "fixed <b>43</b> tickets & more"
    content["projects"][0]["url"] = "https://example.com/it's"

    html = preview.build_html(content, SPEC)

    assert "<script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "fixed &lt;b&gt;43&lt;/b&gt; tickets &amp; more" in html
    assert "it&#39;s" in html and "it's" not in html  # attribute-safe quotes


def test_html_replica_skips_empty_sections_and_inline_dates_when_configured():
    spec = deepcopy(SPEC)
    spec["rightAlignedDates"] = False
    html = preview.build_html(_content("01_junior_short"), spec)

    assert "<h2>PROJECTS</h2>" not in html  # no projects in that fixture
    assert "class='item row'" not in html  # no right tab: dates stay inline
    assert "Soporte técnico nivel 2" in html and "2023 – actualidad" in html


def test_missing_browser_fails_loudly(tmp_path):
    with pytest.raises(preview.PreviewRenderError, match="CHROME_BIN"):
        preview.render_png(_content(), SPEC, chrome=str(tmp_path / "missing-chrome.exe"))


@browser
def test_render_png_is_one_page_at_the_spec_size():
    data = preview.render_png(_content("01_junior_short"), SPEC)

    assert data.startswith(PNG_MAGIC) and len(data) > 5000
    assert Image.open(io.BytesIO(data)).size == (
        round(SPEC["pageSizeIn"]["w"] * preview.PAGE_DPI),
        round(SPEC["pageSizeIn"]["h"] * preview.PAGE_DPI),
    )


@browser
def test_preview_png_b64_is_the_base64_png():
    encoded = preview.preview_png_b64(_content("01_junior_short"), SPEC)

    assert base64.b64decode(encoded).startswith(PNG_MAGIC)
