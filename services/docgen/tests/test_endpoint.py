"""DOC-06 acceptance: private POST /docgen — auth, validation and response contract (§12)."""
from __future__ import annotations

import base64
import json
import threading
import urllib.error
import urllib.request
from http.server import HTTPServer

import pytest

import cvdoc
import endpoint
from api import health
from format_specs import DEFAULT_FORMAT_SPEC as SPEC

SECRET = "test-secret"
PNG = b"\x89PNG\r\n\x1a\nstub-preview"


def _body(**overrides) -> dict:
    body = {"formatSpec": SPEC, "locale": "en",
            "content": cvdoc.fixture_content("02_mid_standard")}
    body.update(overrides)
    return body


def _renderer(content: dict, spec: dict, locale: str) -> bytes:
    return PNG


# ------------------------------------------------------------------ endpoint

def test_generate_requires_the_shared_secret():
    with pytest.raises(endpoint.Unauthorized):
        endpoint.generate(_body(), secret=SECRET, renderer=_renderer)

    with pytest.raises(endpoint.Unauthorized):
        endpoint.generate(_body(), authorization="Bearer wrong", secret=SECRET,
                          renderer=_renderer)


def test_generate_refuses_to_run_without_a_configured_secret():
    with pytest.raises(endpoint.NotConfigured, match="DOCGEN_SHARED_SECRET"):
        endpoint.generate(_body(), secret="", renderer=_renderer)


def test_validate_rejects_a_bullet_without_fact_ids():
    body = _body()
    body["content"]["experience"][0]["bullets"][0]["factIds"] = []

    with pytest.raises(endpoint.InvalidRequest, match="factIds"):
        endpoint.validate(body)


def test_validate_rejects_a_partial_format_spec_and_unknown_locale():
    with pytest.raises(endpoint.InvalidRequest, match="formatSpec is missing"):
        endpoint.validate(_body(formatSpec={"font": "Cambria"}))

    with pytest.raises(endpoint.InvalidRequest, match="locale"):
        endpoint.validate(_body(locale="fr"))


def test_generate_returns_the_docx_and_a_single_preview(monkeypatch):
    calls = []

    def renderer(content, spec, locale):
        calls.append(locale)
        return PNG

    result = endpoint.generate(_body(), authorization=f"Bearer {SECRET}",
                               secret=SECRET, renderer=renderer)

    assert base64.b64decode(result["docx_b64"]).startswith(b"PK")
    assert base64.b64decode(result["preview_png_b64"]) == PNG
    assert calls == ["en"]  # one render, not a second pass for the preview
    assert result["page_count"] == 1
    assert result["iterations"] == 0
    assert result["warning"] is None
    assert set(result) >= {"fill_pct", "line_count", "missing_fonts"}


# ------------------------------------------------------------------- handler

def _call(port: int, path: str, data: bytes, token: str | None = None):
    request = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=data,
                                     method="POST")
    if token is not None:
        request.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(request) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


def _serve(call):
    server = HTTPServer(("127.0.0.1", 0), health.handler)
    thread = threading.Thread(target=server.handle_request, daemon=True)
    thread.start()
    try:
        return call(server.server_port)
    finally:
        thread.join(timeout=5)
        server.server_close()


def test_handler_rejects_a_missing_token(monkeypatch):
    monkeypatch.setenv("DOCGEN_SHARED_SECRET", SECRET)
    status, payload = _serve(lambda port: _call(port, "/docgen", b"{}"))

    assert status == 401
    assert payload["error"]["code"] == "UNAUTHORIZED"


def test_handler_returns_404_off_the_docgen_path():
    status, payload = _serve(lambda port: _call(port, "/public", b"{}"))

    assert status == 404 and payload["error"]["code"] == "NOT_FOUND"


def test_handler_maps_a_malformed_body_to_400(monkeypatch):
    monkeypatch.setenv("DOCGEN_SHARED_SECRET", SECRET)

    status, payload = _serve(
        lambda port: _call(port, "/docgen", b"{not json", token=SECRET))

    assert status == 400 and payload["error"]["code"] == "INVALID_REQUEST"


def test_handler_rejects_an_oversized_body(monkeypatch):
    monkeypatch.setenv("DOCGEN_SHARED_SECRET", SECRET)

    status, payload = _serve(lambda port: _call(
        port, "/docgen", b"x" * (endpoint.MAX_BODY_BYTES + 1), token=SECRET))

    assert status == 413 and payload["error"]["code"] == "PAYLOAD_TOO_LARGE"


def test_handler_returns_the_generation_payload(monkeypatch):
    monkeypatch.setattr(health, "generate", lambda body, authorization=None: {"ok": True})

    status, payload = _serve(lambda port: _call(port, "/docgen", b"{}"))

    assert status == 200 and payload == {"ok": True}


def test_handler_reports_a_missing_browser_as_preview_unavailable(monkeypatch):
    def fail(body, authorization=None):
        raise health.PreviewRenderError("no Chromium-family browser found")

    monkeypatch.setattr(health, "generate", fail)

    status, payload = _serve(lambda port: _call(port, "/docgen", b"{}"))

    assert status == 503 and payload["error"]["code"] == "PREVIEW_UNAVAILABLE"
