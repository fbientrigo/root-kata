import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

EN = {"ROOT_KATA_LANG": "en"}
ES = {"ROOT_KATA_LANG": "es"}

import root_kata.notebook as nb
from root_kata.catalog import get_exercise, localized


class NotebookUxTests(unittest.TestCase):
    def test_starter_cell_is_immediately_runnable(self):
        cell = nb._starter_cell("cpp-sum-positive", "#include <vector>\n")
        self.assertTrue(cell.startswith("%%kata cpp-sum-positive\n"))
        self.assertIn("#include <vector>", cell)
        self.assertTrue(cell.endswith("\n"))

    def test_statement_card_has_problem_constraints_example_and_run_instruction(self):
        with mock.patch.dict(os.environ, EN):
            meta, _ = get_exercise("cpp-sum-positive")
            card = nb._statement_html(localized(meta), "cpp-sum-positive", cell_ready=True)
            self.assertIn("Sum positive values", card)
            self.assertIn("Requirements", card)
            self.assertIn("Example", card)
            self.assertIn("Shift", card)
            self.assertNotIn("rk.check", card)

    def test_statement_card_is_translated_in_spanish_with_stable_technical_terms(self):
        with mock.patch.dict(os.environ, ES):
            meta, _ = get_exercise("cpp-sum-positive")
            card = nb._statement_html(localized(meta), "cpp-sum-positive", cell_ready=True)
            self.assertIn("Suma valores positivos", card)
            self.assertIn("Requisitos", card)
            self.assertIn("Ejemplo", card)
            self.assertIn("Fácil", card)
            # technical API names are never translated
            self.assertIn("std::vector", card)
            self.assertNotIn("Sum positive values", card)

    def test_started_card_has_file_fallback_when_cell_insertion_is_unavailable(self):
        with mock.patch.dict(os.environ, EN):
            meta, _ = get_exercise("cpp-sum-positive")
            card = nb._statement_html(localized(meta), "cpp-sum-positive", cell_ready=False)
            self.assertIn("solution.cpp", card)
            self.assertIn("rk.check", card)
            self.assertNotIn("Start here", card)

    def test_failure_card_prioritises_first_action_and_optional_hint(self):
        meta, _ = get_exercise("cpp-sum-positive")
        result = {
            "status": "failed",
            "summary": "3/4 tests passed",
            "cases": [
                {"name": "empty", "passed": True},
                {"name": "mixed signs", "passed": False, "message": "wrong sum", "expected": 8, "actual": 6},
            ],
            "new_badges": [],
        }
        with mock.patch.dict(os.environ, EN):
            card = nb._format_html(result, meta)
        self.assertIn("Start with the first failing case", card)
        self.assertIn("Expected <code>8</code>; got <code>6</code>", card)
        self.assertIn("Need a hint?", card)

    def test_failure_card_is_translated_in_spanish(self):
        meta, _ = get_exercise("cpp-sum-positive")
        result = {
            "status": "failed",
            "summary": "3/4 tests passed",
            "_sid": "sum.tests_passed",
            "_params": {"n": 3, "m": 4},
            "cases": [
                {"name": "mixed signs", "passed": False, "message": "", "expected": 8, "actual": 6},
                {"name": "empty input", "passed": True},
            ],
            "new_badges": ["first_kata"],
        }
        with mock.patch.dict(os.environ, ES):
            card = nb._format_html(result, localized(meta))
        self.assertIn("Pruebas", card)
        self.assertIn("3/4 pruebas superadas", card)
        self.assertIn("Se esperaba <code>8</code>; se obtuvo <code>6</code>", card)
        self.assertIn("¿Necesitas una pista?", card)
        self.assertIn("signos mixtos", card)
        self.assertIn("entrada vacía", card)
        self.assertIn("Primer kata", card)
        self.assertNotIn("Need a hint?", card)
        self.assertNotIn("First Kata", card)

    def test_failure_card_shows_semantic_test_progress(self):
        meta, _ = get_exercise("cpp-sum-positive")
        result = {
            "status": "failed",
            "summary": "3/4 tests passed",
            "cases": [
                {"name": "one", "passed": True},
                {"name": "two", "passed": True},
                {"name": "three", "passed": False, "message": "wrong result"},
                {"name": "four", "passed": True},
            ],
            "new_badges": [],
        }
        with mock.patch.dict(os.environ, EN):
            card = nb._format_html(result, meta)
        self.assertIn('<progress value="3" max="4"', card)
        self.assertIn("3 / 4", card)
        self.assertIn(">Tests</span>", card)

    def test_progress_primitive_clamps_counts_and_is_reusable(self):
        bar = nb._progress_html(9, 4, label="Lesson steps")
        self.assertIn('<progress value="4" max="4"', bar)
        self.assertIn("Lesson steps", bar)
        self.assertIn("4 / 4", bar)
        self.assertEqual(nb._progress_html(0, 0), "")

    def test_start_preserves_existing_solution_and_uses_it_for_inserted_cell(self):
        old_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as t:
            os.chdir(t)
            try:
                path = Path("kata/cpp-sum-positive/solution.cpp")
                path.parent.mkdir(parents=True)
                custom = "// my current work\n"
                path.write_text(custom, encoding="utf-8")
                with mock.patch.object(nb, "_in_notebook", return_value=True), \
                     mock.patch.object(nb, "_prepare_notebook_cell", return_value=True) as prepare, \
                     mock.patch.object(nb, "_display"):
                    returned = nb.start("cpp-sum-positive")
                self.assertIsNone(returned)
                self.assertEqual(path.read_text(encoding="utf-8"), custom)
                prepare.assert_called_once_with("cpp-sum-positive", custom)
            finally:
                os.chdir(old_cwd)

    def test_public_notebook_helpers_are_exported(self):
        import root_kata as rk

        self.assertTrue(callable(rk.hint))
        self.assertTrue(callable(rk.export))


if __name__ == "__main__":
    unittest.main()


class ContinueLinkTests(unittest.TestCase):
    def test_passed_result_offers_one_obvious_next_action(self):
        meta, _ = get_exercise("cpp-sum-positive")
        result = {
            "status": "passed",
            "summary": "4/4 tests passed",
            "_sid": "sum.tests_passed",
            "_params": {"n": 4, "m": 4},
            "cases": [{"name": "all", "passed": True}],
            "new_badges": ["first_kata"],
            "exercise_id": "cpp-sum-positive",
        }
        with mock.patch.dict(os.environ, ES):
            card = nb._format_html(result, localized(meta))
        self.assertIn("Continuar →", card)
        self.assertIn("https://fbientrigo.github.io/root-kata/?solved=cpp-sum-positive&amp;badge=first_kata", card)
        self.assertIn("Primer kata", card)

    def test_failed_result_has_no_continue_action(self):
        meta, _ = get_exercise("cpp-sum-positive")
        result = {"status": "failed", "summary": "0/4 tests passed",
                  "_sid": "sum.tests_passed", "_params": {"n": 0, "m": 4},
                  "cases": [{"name": "x", "passed": False, "message": ""}], "new_badges": []}
        with mock.patch.dict(os.environ, EN):
            card = nb._format_html(result, meta)
        self.assertNotIn("Continue →", card)
