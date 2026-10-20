"""`POST /docgen`: validate a GenerateRequest, converge, render one preview (§12).

The endpoint is the private boundary between the web app and the generator. It owns
transport concerns only: shared-secret auth, request validation and the response shape.
Pagination and rendering stay in `converge.py` / `preview.py`; docgen holds no business
logic, so the convergence loop runs with no compress/enrich callbacks and reports
`warning: "over_one_page"` when the tree does not fit (TR-FMT-1).
"""
from __future__ import annotations

import base64
import hmac
import os
from io import BytesIO

from converge import converge
from format_specs import DEFAULT_FORMAT_SPEC
from preview import render_png

MAX_BODY_BYTES = 512 * 1024
_SECTIONS = ("experience", "projects", "education", "certifications", "skills", "languages")


class DocgenError(Exception):
    """Base class for request failures; `status` is the HTTP status to return."""

    status = 400
    code = "INVALID_REQUEST"


class NotConfigured(DocgenError):
    status = 503
    code = "DOCGEN_NOT_CONFIGURED"


class Unauthorized(DocgenError):
    status = 401
    code = "UNAUTHORIZED"


class InvalidRequest(DocgenError):
    status = 400
    code = "INVALID_REQUEST"


class PayloadTooLarge(DocgenError):
    status = 413
    code = "PAYLOAD_TOO_LARGE"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise InvalidRequest(message)


def _bullets(item: dict, where: str) -> None:
    bullets = item.get("bullets")
    _require(isinstance(bullets, list), f"{where}.bullets must be an array")
    for index, bullet in enumerate(bullets):
        label = f"{where}.bullets[{index}]"
        _require(isinstance(bullet, dict), f"{label} must be an object")
        _require(isinstance(bullet.get("text"), str), f"{label}.text must be a string")
        fact_ids = bullet.get("factIds")
        _require(isinstance(fact_ids, list) and fact_ids
                 and all(isinstance(fact_id, str) for fact_id in fact_ids),
                 f"{label}.factIds must be a non-empty array of strings")


def validate(body: dict) -> tuple[dict, dict, str]:
    """Return `(content, format_spec, locale)` or raise `InvalidRequest`.

    Mirrors `GenerateRequestSchema` (§6) closely enough that a malformed tree is a 400,
    never a 500 from deep inside the builder.
    """
    _require(isinstance(body, dict), "body must be a JSON object")
    spec = body.get("formatSpec")
    _require(isinstance(spec, dict) and spec, "formatSpec must be a non-empty object")
    locale = body.get("locale", "en")
    _require(locale in ("en", "es"), "locale must be 'en' or 'es'")
    missing = [key for key in DEFAULT_FORMAT_SPEC if key not in spec]
    _require(not missing, f"formatSpec is missing: {', '.join(missing)}")
    _require(isinstance(spec["headings"], dict) and locale in spec["headings"],
             f"formatSpec.headings.{locale} is required")

    content = body.get("content")
    _require(isinstance(content, dict), "content must be an object")
    header = content.get("header")
    _require(isinstance(header, dict)
             and all(isinstance(header.get(key), str) and header.get(key)
                     for key in ("name", "contactLine")),
             "content.header.name and content.header.contactLine are required strings")
    _require(isinstance(content.get("summary"), str), "content.summary must be a string")
    for section in _SECTIONS:
        _require(isinstance(content.get(section), list), f"content.{section} must be an array")

    for index, item in enumerate(content["experience"]):
        where = f"content.experience[{index}]"
        _require(isinstance(item, dict), f"{where} must be an object")
        for key in ("company", "role", "start", "end"):
            _require(isinstance(item.get(key), str), f"{where}.{key} must be a string")
        _bullets(item, where)

    for index, item in enumerate(content["projects"]):
        where = f"content.projects[{index}]"
        _require(isinstance(item, dict), f"{where} must be an object")
        _require(isinstance(item.get("name"), str), f"{where}.name must be a string")
        _bullets(item, where)

    for section in ("education", "certifications", "skills", "languages"):
        _require(all(isinstance(entry, str) for entry in content[section]),
                 f"content.{section} must contain strings")

    return content, spec, locale


def _authorized(authorization: str | None, secret: str) -> bool:
    prefix = "Bearer "
    if not authorization or not authorization.startswith(prefix):
        return False
    return hmac.compare_digest(authorization[len(prefix):].strip().encode(), secret.encode())


def generate(body: dict, *, authorization: str | None = None,
             secret: str | None = None, renderer=render_png) -> dict:
    """Authenticate, validate, converge and render one preview.

    `secret` defaults to `DOCGEN_SHARED_SECRET`; an unset secret refuses every request
    instead of running unauthenticated. The renderer is injectable so tests do not need
    a browser; production uses `preview.render_png`.
    """
    secret = secret if secret is not None else os.environ.get("DOCGEN_SHARED_SECRET")
    if not secret:
        raise NotConfigured("DOCGEN_SHARED_SECRET is not set; refusing to generate")
    if not _authorized(authorization, secret):
        raise Unauthorized("missing or invalid bearer token")

    content, spec, locale = validate(body)
    result = converge(content, spec, locale=locale)
    preview = renderer(result["content"], spec, locale)
    docx = BytesIO()
    result["docx"].save(docx)
    return {
        "docx_b64": base64.b64encode(docx.getvalue()).decode("ascii"),
        "preview_png_b64": base64.b64encode(preview).decode("ascii"),
        "fill_pct": result["fill_pct"],
        "line_count": result["line_count"],
        "page_count": result["page_count"],
        "missing_fonts": result["missing_fonts"],
        "iterations": result["iterations"],
        "warning": result["warning"],
    }


def error_body(exc: DocgenError) -> dict:
    return {"error": {"code": exc.code, "message": str(exc), "details": {}}}
