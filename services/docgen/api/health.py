"""Health endpoint for the docgen service."""

import json
from http.server import BaseHTTPRequestHandler

BODY = json.dumps({"service": "docgen", "status": "ok"})


class handler(BaseHTTPRequestHandler):
    """Report service liveness as a Vercel Python function response."""

    def do_GET(self):
        data = BODY.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)
