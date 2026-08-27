import html
import json
import sys
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from root_kata.catalog import exercise_payload
from root_kata.cli import build_parser
from root_kata.web_server import DEFAULT_HOST, create_server


class ServeConfigTests(unittest.TestCase):
    def test_cli_serve_defaults_to_local_port_and_accepts_override(self):
        args = build_parser().parse_args(["serve"])
        self.assertEqual(args.command, "serve")
        self.assertEqual(args.port, 8765)

        args = build_parser().parse_args(["serve", "--port", "9001"])
        self.assertEqual(args.port, 9001)

    def test_server_binds_to_localhost_by_default(self):
        server = create_server(port=0, site_root=ROOT / "docs")
        try:
            self.assertEqual(server.server_address[0], DEFAULT_HOST)
            self.assertGreater(server.server_address[1], 0)
        finally:
            server.server_close()


class ReadOnlyApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = create_server(port=0, site_root=ROOT / "docs")
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        host, port = cls.server.server_address[:2]
        cls.base = f"http://{host}:{port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def get_json(self, path):
        with urlopen(self.base + path, timeout=2) as response:
            self.assertEqual(response.headers.get_content_type(), "application/json")
            return json.load(response)

    def get_html(self, path):
        with urlopen(self.base + path, timeout=2) as response:
            self.assertEqual(response.headers.get_content_type(), "text/html")
            return response.read().decode("utf-8")

    def test_static_root_serves_the_existing_root_kata_ui(self):
        markup = self.get_html("/")
        self.assertIn("ROOT Kata", markup)
        self.assertIn("<!doctype html>", markup.lower())

    def test_catalog_endpoint_uses_the_real_catalog(self):
        payload = self.get_json("/api/exercises")
        ids = {item["id"] for item in payload["exercises"]}
        self.assertIn("cpp-hello-world", ids)
        self.assertIn("cpp-root-histogram", ids)

    def test_exercise_endpoint_includes_the_real_starter(self):
        payload = self.get_json("/api/exercises/cpp-hello-world")
        self.assertEqual(payload["id"], "cpp-hello-world")
        self.assertIn("starter_code", payload)
        self.assertIn("say_hello", payload["starter_code"])

    def test_workspace_uses_repository_statement_and_exact_starter(self):
        payload = exercise_payload("cpp-hello-world")
        markup = self.get_html("/kata/cpp-hello-world?lang=es")
        decoded = html.unescape(markup)
        self.assertIn("Hola, mundo", decoded)
        self.assertIn(payload["starter_code"], decoded)
        self.assertIn('id="code-editor"', markup)
        self.assertIn('class="workspace-grid"', markup)
        self.assertNotIn("Jupyter", markup)

    def test_workspace_localizes_without_changing_starter(self):
        payload = exercise_payload("cpp-hello-world")
        markup = self.get_html("/kata/cpp-hello-world?lang=en")
        decoded = html.unescape(markup)
        self.assertIn("Hello, world", decoded)
        self.assertIn(payload["starter_code"], decoded)
        self.assertIn('href="/kata/cpp-hello-world?lang=es"', markup)

    def test_unknown_workspace_is_404(self):
        with self.assertRaises(HTTPError) as caught:
            urlopen(self.base + "/kata/not-real", timeout=2)
        self.assertEqual(caught.exception.code, 404)

    def test_unknown_api_route_is_json_404(self):
        with self.assertRaises(HTTPError) as caught:
            urlopen(self.base + "/api/not-real", timeout=2)
        self.assertEqual(caught.exception.code, 404)
        payload = json.loads(caught.exception.read().decode("utf-8"))
        self.assertEqual(payload["error"], "not_found")


if __name__ == "__main__":
    unittest.main()
