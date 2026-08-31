"""Minimal trusted-local HTTP server for the ROOT Kata learner UI."""
from __future__ import annotations

import html
import json
import os
import tempfile
from functools import partial
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

from . import i18n
from .catalog import case_label, exercise_payload, list_exercises, localized, message_label, repository_root
from .grader import grade_code
from .notebook_ui import _summary

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
MAX_RUN_BODY_BYTES = 256 * 1024
_LANGS = {"es", "en"}
_STATUS_KEYS = {
    "passed": "status.passed", "failed": "status.failed", "compile_error": "status.compile_error",
    "runtime_error": "status.runtime_error", "solution_error": "status.solution_error", "timeout": "status.timeout",
    "runtime_missing": "status.runtime_missing", "harness_error": "status.harness_error", "grader_error": "status.grader_error",
}

_WORKSPACE_UI = {
    "es": {
        "back": "← Todos los katas",
        "code": "Código",
        "edit_help": "Edita el starter aquí y pulsa Ejecutar para ver el resultado.",
        "requirements": "Requisitos",
        "examples": "Ejemplos",
        "hints": "Pistas",
        "input": "Entrada",
        "output": "Salida",
        "run": "Ejecutar",
        "running": "Ejecutando…",
        "not_running": "Editor listo",
        "feedback": "Resultado",
        "switch": "EN",
    },
    "en": {
        "back": "← All katas",
        "code": "Code",
        "edit_help": "Edit the starter here, then press Run to see the result.",
        "requirements": "Requirements",
        "examples": "Examples",
        "hints": "Hints",
        "input": "Input",
        "output": "Output",
        "run": "Run",
        "running": "Running…",
        "not_running": "Editor ready",
        "feedback": "Result",
        "switch": "ES",
    },
}


class RootKataHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


class RootKataHandler(SimpleHTTPRequestHandler):
    """Serve the learner UI and trusted-local execution API."""

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
        <form id="run-form" class="run-form">
          <button id="run-button" class="button primary large" type="submit">{esc(ui["run"])}</button>
        </form>
        <p class="workspace-status" role="status">{esc(ui["not_running"])}</p>
        <section id="run-feedback" class="run-feedback" aria-live="polite" aria-labelledby="run-feedback-title" hidden>
          <h2 id="run-feedback-title">{esc(ui["feedback"])}</h2>
        </section>
      </section>
    </div>
</main>
<script src="/site.js" defer></script>
</body>
</html>
"""
        self._send_html(HTTPStatus.OK, markup)

    def _present_result(self, result: dict, metadata: dict, lang: str) -> dict:
        public = dict(result)
        status = str(public.get("status", ""))
        public["status_label"] = i18n.translate(_STATUS_KEYS.get(status, "status.check_result"), lang)
        public["summary"] = _summary(public, lang=lang)
        public["cases"] = []
        for item in result.get("cases", []):
            case = dict(item)
            case["name"] = case_label(metadata, str(case.get("name", "")), lang=lang)
            if "message" in case:
                case["message"] = message_label(metadata, case.get("message"), lang=lang)
            if not case.get("passed") and case.get("expected") is not None:
                case["expected_got"] = i18n.translate(
                    "expected_got_text", lang, expected=case.get("expected"), actual=case.get("actual")
                )
            public["cases"].append(case)

        work_dir = public.get("work_dir")
        if work_dir:
            for field in ("stdout", "stderr"):
                text = public.get(field)
                if isinstance(text, str):
                    for separator in (os.sep, "/", "\\"):
                        text = text.replace(str(work_dir) + separator, "")
                    public[field] = text.replace(str(work_dir), "")
        for internal_key in ("work_dir", "preview", "_sid", "_params"):
            public.pop(internal_key, None)
        return public

    def _run_request(self) -> None:
        if self.headers.get_content_type() != "application/json":
            self._send_json(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, {"error": "content_type_required"})
            return
        content_length = self.headers.get("Content-Length")
        try:
            length = int(content_length) if content_length is not None else -1
        except ValueError:
            length = -1
        if length < 0:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid_request", "message": "Content-Length is required"})
            return
        if length > MAX_RUN_BODY_BYTES:
            self._send_json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"error": "request_too_large"})
            return
        try:
            request = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid_json"})
            return
        if not isinstance(request, dict):
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid_request", "message": "JSON object required"})
            return

        exercise_id = request.get("exercise_id")
        code = request.get("code")
        if not isinstance(exercise_id, str) or not exercise_id:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid_request", "message": "exercise_id must be a string"})
            return
        if not isinstance(code, str):
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid_request", "message": "code must be a string"})
            return
        metadata = self._exercise(exercise_id)
        if metadata is None:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "exercise_not_found"})
            return

        lang = request.get("lang", "es")
        if not isinstance(lang, str) or lang not in _LANGS:
            lang = "es"
        with tempfile.TemporaryDirectory(prefix="root-kata-web-") as attempt:
            result = grade_code(exercise_id, code, work_root=Path(attempt))
        self._send_json(HTTPStatus.OK, self._present_result(result, metadata, lang))

    def do_POST(self) -> None:  # noqa: N802 - stdlib handler API
        path = urlsplit(self.path).path.rstrip("/") or "/"
        if path == "/api/run":
            self._run_request()
            return
        self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})

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
