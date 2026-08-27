"""Minimal trusted-local HTTP server for the ROOT Kata learner UI.

Phase 1 serves the existing catalog plus a small server-rendered kata workspace.
Browser-triggered code execution belongs to the later execution slice; this
module still exposes only read-only exercise data.
"""
from __future__ import annotations

import html
import json
from functools import partial
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

from .catalog import exercise_payload, list_exercises, localized, repository_root

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
_LANGS = {"es", "en"}

_WORKSPACE_UI = {
    "es": {
        "back": "← Todos los katas",
        "code": "Código",
        "edit_help": "Edita el starter directamente aquí. La ejecución se conecta en el siguiente hito.",
        "requirements": "Requisitos",
        "examples": "Ejemplos",
        "hints": "Pistas",
        "input": "Entrada",
        "output": "Salida",
        "not_running": "Editor listo · ejecución aún no habilitada",
        "switch": "EN",
    },
    "en": {
        "back": "← All katas",
        "code": "Code",
        "edit_help": "Edit the starter directly here. Execution is connected in the next milestone.",
        "requirements": "Requirements",
        "examples": "Examples",
        "hints": "Hints",
        "input": "Input",
        "output": "Output",
        "not_running": "Editor ready · execution not enabled yet",
        "switch": "ES",
    },
}


class RootKataHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


class RootKataHandler(SimpleHTTPRequestHandler):
    """Serve the learner UI plus a tiny read-only catalog API."""

    server_version = "ROOTKataHTTP/0.2"

    def _send_bytes(self, status: HTTPStatus, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, status: HTTPStatus, payload: object) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self._send_bytes(status, body, "application/json; charset=utf-8")

    def _send_html(self, status: HTTPStatus, markup: str) -> None:
        self._send_bytes(status, markup.encode("utf-8"), "text/html; charset=utf-8")

    def _exercise(self, exercise_id: str) -> dict | None:
        try:
            payload = exercise_payload(exercise_id)
        except (KeyError, OSError, ValueError):
            return None
        if not payload.get("published", True):
            return None
        return payload

    def _workspace(self, exercise_id: str, lang: str) -> None:
        payload = self._exercise(exercise_id)
        if payload is None:
            self._send_html(HTTPStatus.NOT_FOUND, "<h1>404 · kata not found</h1>")
            return

        lang = lang if lang in _LANGS else "es"
        view = localized(payload, lang)
        ui = _WORKSPACE_UI[lang]
        esc = lambda value: html.escape(str(value), quote=True)

        requirements = "".join(f"<li>{esc(item)}</li>" for item in view.get("requirements", []))
        hints = "".join(f"<li>{esc(item)}</li>" for item in view.get("hints", []))
        examples = []
        for item in view.get("examples", []):
            explanation = f"<p>{esc(item.get('explanation', ''))}</p>" if item.get("explanation") else ""
            examples.append(
                '<div class="workspace-example">'
                f'<div><span>{esc(ui["input"])}</span><code>{esc(item.get("input", ""))}</code></div>'
                f'<div><span>{esc(ui["output"])}</span><code>{esc(item.get("output", ""))}</code></div>'
                f"{explanation}</div>"
            )

        other_lang = "en" if lang == "es" else "es"
        runtime = "ROOT + C++" if view.get("requires") else "C++17"
        source = esc(payload["starter_code"])
        markup = f"""<!doctype html>
<html lang="{lang}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(view["title"])} · ROOT Kata</title>
  <link rel="stylesheet" href="/styles.css">
</head>
<body>
  <header class="site-header">
    <a class="brand" href="/">ROOT Kata</a>
    <span>{esc(runtime)}</span>
    <nav class="lang-switch" aria-label="Language">
      <a href="/kata/{esc(exercise_id)}?lang={other_lang}" lang="{other_lang}" hreflang="{other_lang}">{ui["switch"]}</a>
    </nav>
  </header>
  <main class="workspace">
    <a class="back-link" href="/">{esc(ui["back"])}</a>
    <div class="workspace-grid">
      <article class="workspace-problem" aria-labelledby="kata-title">
        <div class="problem-meta">
          <span class="difficulty">{esc(view.get("difficulty", ""))}</span>
          <span>{esc(runtime)}</span>
        </div>
        <h1 id="kata-title">{esc(view["title"])}</h1>
        <p class="lead">{esc(view.get("summary", ""))}</p>
        <section>
          <p>{esc(view.get("description", ""))}</p>
        </section>
        {'<section><h2>' + esc(ui["examples"]) + '</h2>' + ''.join(examples) + '</section>' if examples else ''}
        {'<section><h2>' + esc(ui["requirements"]) + '</h2><ul>' + requirements + '</ul></section>' if requirements else ''}
        {'<section><h2>' + esc(ui["hints"]) + '</h2><ul>' + hints + '</ul></section>' if hints else ''}
      </article>
      <section class="workspace-editor-panel" aria-labelledby="editor-title">
        <div class="workspace-editor-head">
          <div>
            <h2 id="editor-title">{esc(ui["code"])}</h2>
            <p>{esc(ui["edit_help"])}</p>
          </div>
          <span class="workspace-runtime">{esc(runtime)}</span>
        </div>
        <label class="visually-hidden" for="code-editor">{esc(ui["code"])}</label>
        <textarea id="code-editor" class="code-editor" spellcheck="false" autocapitalize="off" autocomplete="off" wrap="off">{source}</textarea>
        <p class="workspace-status" role="status">{esc(ui["not_running"])}</p>
      </section>
    </div>
  </main>
</body>
</html>
"""
        self._send_html(HTTPStatus.OK, markup)

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
            payload = self._exercise(exercise_id)
            if payload is None:
                self._send_json(HTTPStatus.NOT_FOUND, {"error": "exercise_not_found"})
            else:
                self._send_json(HTTPStatus.OK, payload)
            return
        if path.startswith("/api/"):
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return

        if path.startswith("/kata/"):
            exercise_id = unquote(path.removeprefix("/kata/"))
            if not exercise_id or "/" in exercise_id:
                self._send_html(HTTPStatus.NOT_FOUND, "<h1>404 · kata not found</h1>")
                return
            lang = parse_qs(parsed.query).get("lang", ["es"])[0]
            self._workspace(exercise_id, lang)
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
