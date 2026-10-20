"""Docgen service entrypoint: GET health + the private POST /docgen endpoint (§12).

Vercel routes every request to this single Python entrypoint (SETUP-06), so the paths are
dispatched here. `/docgen` is server-to-server only: it needs the shared bearer secret.
"""
import json
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlsplit

from endpoint import (
    MAX_BODY_BYTES,
    DocgenError,
    InvalidRequest,
    PayloadTooLarge,
    error_body,
    generate,
)
from preview import PreviewRenderError

HEALTH = {"service": "docgen", "status": "ok"}
DOCGEN_PATHS = ("/docgen", "/api/docgen")


def _error(code: str, message: str) -> dict:
    return {"error": {"code": code, "message": message, "details": {}}}


class handler(BaseHTTPRequestHandler):
    """Report liveness and generate documents as a Vercel Python function."""

    def do_GET(self):
        self._json(200, HEALTH)

    def do_POST(self):
        path = urlsplit(self.path).path.rstrip("/")
        if path not in DOCGEN_PATHS:
            self._json(404, _error("NOT_FOUND", "not found"))
            return
        try:
            body = self._read_json()
            self._json(200, generate(body,
                                     authorization=self.headers.get("Authorization")))
        except DocgenError as exc:
            self._json(exc.status, error_body(exc))
        except PreviewRenderError as exc:
            self._json(503, _error("PREVIEW_UNAVAILABLE", str(exc)))
        except Exception as exc:  # never leak a stack trace or CV content to the caller
            self.log_error("docgen failed: %s", type(exc).__name__)
            self._json(500, _error("DOCGEN_FAILED", "document generation failed"))

    def _read_json(self) -> dict:
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            raise InvalidRequest("Content-Length must be an integer")
        if length > MAX_BODY_BYTES:
            raise PayloadTooLarge(f"body exceeds {MAX_BODY_BYTES} bytes")
        raw = self.rfile.read(length)
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError):
            raise InvalidRequest("body must be valid JSON")

    def _json(self, status: int, payload: dict) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)
