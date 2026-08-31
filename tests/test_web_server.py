from concurrent.futures import ThreadPoolExecutor
import html
import json
import sys
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from unittest import mock
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from root_kata.catalog import exercise_payload
from root_kata.cli import build_parser
from root_kata.cpp_runner import _which_compiler
from root_kata.web_server import DEFAULT_HOST, MAX_RUN_BODY_BYTES, create_server


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

    def post_json(self, payload, *, raw=False):
        body = payload if raw else json.dumps(payload).encode("utf-8")
        request = Request(self.base + "/api/run", data=body, method="POST",
                          headers={"Content-Type": "application/json"})
        try:
            with urlopen(request, timeout=15) as response:
                return response.status, json.load(response)
        except HTTPError as exc:
            return exc.code, json.loads(exc.read().decode("utf-8"))

    def post_raw(self, body, content_type):
        request = Request(self.base + "/api/run", data=body, method="POST",
                          headers={"Content-Type": content_type})
        try:
            with urlopen(request, timeout=2) as response:
                return response.status, json.load(response)
        except HTTPError as exc:
            return exc.code, json.loads(exc.read().decode("utf-8"))

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
        self.assertIn('id="run-button"', markup)
        self.assertIn('id="run-feedback"', markup)
        self.assertIn('src="/site.js"', markup)
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

    def test_run_endpoint_adapts_existing_result_without_internal_paths(self):
        result = {"status": "passed", "passed": True, "summary": "2/2 tests passed",
                  "cases": [], "stdout": "", "stderr": "", "work_dir": "/tmp/private",
                  "preview": {"path": "/tmp/private/plot.png"}, "_sid": "internal", "_params": {}}
        with mock.patch("root_kata.web_server.grade_code", return_value=result) as grade:
            status, payload = self.post_json({"exercise_id": "cpp-hello-world", "code": "source"})
        self.assertEqual(status, 200)
        args, kwargs = grade.call_args
        self.assertEqual(args, ("cpp-hello-world", "source"))
        self.assertIn("work_root", kwargs)
        self.assertEqual(payload["status"], "passed")
        self.assertNotIn("work_dir", payload)
        self.assertNotIn("preview", payload)
        self.assertNotIn("_sid", payload)
        self.assertNotIn("_params", payload)

    def test_run_endpoint_localizes_summary_cases_messages_and_expected_got(self):
        result = {
            "status": "failed", "passed": False, "summary": "raw summary", "_sid": "sum.tests_passed",
            "_params": {"n": 1, "m": 2}, "stdout": "", "stderr": "",
            "cases": [
                {"name": "prints something", "passed": True, "message": "Passed"},
                {"name": "exact output", "passed": False, "message": "Values differ", "expected": "'a'", "actual": "'b'"},
            ],
        }
        with mock.patch("root_kata.web_server.grade_code", return_value=result):
            es_status, es = self.post_json({"exercise_id": "cpp-hello-world", "code": "source", "lang": "es"})
            en_status, en = self.post_json({"exercise_id": "cpp-hello-world", "code": "source", "lang": "en"})
        self.assertEqual((es_status, en_status), (200, 200))
        self.assertEqual(es["status_label"], "Aún no")
        self.assertEqual(es["summary"], "1/2 pruebas superadas")
        self.assertEqual([case["name"] for case in es["cases"]], ["imprime algo", "salida exacta"])
        self.assertIn("Los valores difieren", es["cases"][1]["message"])
        self.assertIn("esperaba", es["cases"][1]["expected_got"])
        self.assertEqual(en["status_label"], "Not yet")
        self.assertEqual(en["summary"], "1/2 tests passed")
        self.assertEqual([case["name"] for case in en["cases"]], ["prints something", "exact output"])
        self.assertIn("Values differ", en["cases"][1]["message"])
        self.assertIn("expected", en["cases"][1]["expected_got"])

    def test_concurrent_same_exercise_runs_use_distinct_attempt_workspaces(self):
        barrier = threading.Barrier(2)
        observed = {}

        def fake_grade(exercise_id, code, *, work_root):
            source = work_root / "solution.cpp"
            source.write_text(code, encoding="utf-8")
            barrier.wait(timeout=5)
            observed[code] = (str(work_root), source.read_text(encoding="utf-8"))
            return {"status": "passed", "passed": True, "summary": code, "cases": [], "stdout": "", "stderr": ""}

        codes = ("source A", "source B")
        with mock.patch("root_kata.web_server.grade_code", side_effect=fake_grade):
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(lambda code: self.post_json({"exercise_id": "cpp-hello-world", "code": code}), codes))
        self.assertEqual([status for status, _ in results], [200, 200])
        self.assertEqual({observed[code][1] for code in codes}, set(codes))
        self.assertEqual(len({observed[code][0] for code in codes}), 2)

    def test_run_endpoint_rejects_invalid_json_and_input(self):
        status, payload = self.post_raw(b"{}", "text/plain")
        self.assertEqual(status, 415)
        self.assertEqual(payload["error"], "content_type_required")

        status, payload = self.post_json(b"{", raw=True)
        self.assertEqual(status, 400)
        self.assertEqual(payload["error"], "invalid_json")

        status, payload = self.post_json({"exercise_id": "cpp-hello-world"})
        self.assertEqual(status, 400)
        self.assertEqual(payload["error"], "invalid_request")

    def test_run_endpoint_rejects_unknown_exercise_without_executing(self):
        with mock.patch("root_kata.web_server.grade_code") as grade:
            status, payload = self.post_json({"exercise_id": "not-real", "code": "source"})
        self.assertEqual(status, 404)
        self.assertEqual(payload["error"], "exercise_not_found")
        grade.assert_not_called()

    def test_run_endpoint_rejects_unexpectedly_large_request(self):
        status, payload = self.post_json({"exercise_id": "cpp-hello-world", "code": "x" * MAX_RUN_BODY_BYTES})
        self.assertEqual(status, 413)
        self.assertEqual(payload["error"], "request_too_large")

    @unittest.skipIf(_which_compiler() is None, "no C++ compiler")
    def test_run_endpoint_wrong_cpp_source_returns_failed_semantics(self):
        status, payload = self.post_json({"exercise_id": "cpp-hello-world", "code": "#include <iostream>\nvoid say_hello() {}\n"})
        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "failed")
        self.assertFalse(payload["passed"])
        self.assertEqual(len(payload["cases"]), 2)

    @unittest.skipIf(_which_compiler() is None, "no C++ compiler")
    def test_run_endpoint_correct_cpp_source_returns_passed_semantics(self):
        code = '#include <iostream>\nvoid say_hello(){std::cout << "Hello, world!" << std::endl;}\n'
        status, payload = self.post_json({"exercise_id": "cpp-hello-world", "code": code})
        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "passed", payload)
        self.assertTrue(payload["passed"])

    @unittest.skipIf(_which_compiler() is None, "no C++ compiler")
    def test_run_endpoint_compile_error_does_not_expose_workspace_path(self):
        code = "#include <iostream>\nvoid say_hello(){\n"
        status, payload = self.post_json({"exercise_id": "cpp-hello-world", "code": code})
        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "compile_error")
        serialized = json.dumps(payload)
        self.assertNotIn("root-kata-web-", serialized)
        self.assertIn("solution.cpp", serialized)


if __name__ == "__main__":
    unittest.main()
