"""Minimal trusted-local HTTP server for the ROOT Kata learner UI.

Phase 1 deliberately exposes only read-only catalog data plus the generated
static site. Browser-triggered code execution belongs to the later execution
slice; this module does not add a second runner or make the current runner
network-accessible.
"""
from __future__ import annotations

import json
from functools import partial
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

from .catalog import exercise_payload, list_exercises, repository_root

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765


class RootKataHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


class RootKataHandler(SimpleHTTPRequestHandler):
    """Serve the generated learner UI and a tiny read-only catalog API."""

    server_version = "ROOTKataHTTP/0.1"

    def _send_json(self, status: HTTPStatus, payload: object) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _exercise(self, exercise_id: str) -> None:
        try:
            payload = exercise_payload(exercise_id)
        except (KeyError, OSError, ValueError):
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "exercise_not_found"})
            return
        if not payload.get("published", True):
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "exercise_not_found"})
            return
        self._send_json(HTTPStatus.OK, payload)

    def do_GET(self) -> None:  # noqa: N802 - stdlib handler API
        parsed = urlsplit(self.path)
        path = parsed.path.rstrip("/") or "/"

        if path == "/api/health":
            self._send_json(HTTPStatus.OK, {"status": "ok"})
            return
        if path == "/api/exercises":
            self._send_json(HTTPStatus.OK, {"exercises": list_exercises()})
            return
        if path.startswith("/api/exercises/"):
            exercise_id = unquote(path.removeprefix("/api/exercises/"))
            if not exercise_id or "/" in exercise_id:
                self._send_json(HTTPStatus.NOT_FOUND, {"error": "exercise_not_found"})
                return
            self._exercise(exercise_id)
            return
        if path.startswith("/api/"):
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return

        super().do_GET()


def default_site_root() -> Path:
    return repository_root() / "docs"


def create_server(
    *,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    site_root: Path | None = None,
) -> RootKataHTTPServer:
    """Create the local server without starting its blocking serve loop."""

    root = (site_root or default_site_root()).resolve()
    if not (root / "index.html").is_file():
        raise RuntimeError(f"ROOT Kata web UI not found at {root}")

    handler = partial(RootKataHandler, directory=str(root))
    return RootKataHTTPServer((host, port), handler)


def serve(*, port: int = DEFAULT_PORT, host: str = DEFAULT_HOST) -> int:
    """Run the trusted-local ROOT Kata web server until Ctrl+C."""

    httpd = create_server(host=host, port=port)
    bound_host, bound_port = httpd.server_address[:2]
    url = f"http://{bound_host}:{bound_port}/"
    print(f"ROOT Kata: {url}")
    print("Press Ctrl+C to stop.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
    return 0
