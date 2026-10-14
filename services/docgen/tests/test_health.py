"""Contract tests for the docgen health endpoint."""

import json
import threading
import urllib.request
from http.server import HTTPServer

from api.health import handler


def test_health_returns_ok_json():
    server = HTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.handle_request, daemon=True)
    thread.start()
    try:
        with urllib.request.urlopen(
            f"http://127.0.0.1:{server.server_port}/api/health"
        ) as response:
            status = response.status
            content_type = response.headers["Content-Type"]
            body = response.read()
    finally:
        thread.join(timeout=5)
        server.server_close()
    assert status == 200
    assert content_type == "application/json"
    assert json.loads(body) == {"service": "docgen", "status": "ok"}
