import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from root_kata.catalog import list_exercises


def public_ids():
    return [item["id"] for item in list_exercises()]


def setUpModule():
    subprocess.run([sys.executable, str(ROOT / "scripts" / "build_pages.py")], check=True, cwd=ROOT)


class GitHubPagesTests(unittest.TestCase):
    def test_pages_publish_current_catalog_per_language(self):
        expected = sorted(public_ids())
        for problems_dir in (ROOT / "docs" / "problems", ROOT / "docs" / "en" / "problems"):
            pages = sorted(p.stem for p in problems_dir.glob("*.html"))
            self.assertEqual(pages, expected)

    def test_spanish_is_primary_and_english_is_nested(self):
        self.assertTrue((ROOT / "docs" / "index.html").is_file())
        html_es = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
        html_en = (ROOT / "docs" / "en" / "index.html").read_text(encoding="utf-8")
        expected_actions = len(public_ids()) + 1
        self.assertEqual(html_es.count("Abrir en Jupyter"), expected_actions)
        self.assertEqual(html_en.count("Open in Jupyter"), expected_actions)
        self.assertNotIn("/api/", html_es)
        self.assertIn('lang="es"', html_es)
        self.assertIn('lang="en"', html_en)
        self.assertIn("Introductorio", html_es)
        self.assertIn("Introductory", html_en)

    def test_problem_pages_link_references_and_use_stable_ids(self):
        markup = (ROOT / "docs" / "problems" / "cpp-root-histogram.html").read_text(encoding="utf-8")
        self.assertIn("https://root.cern.ch/doc/master/classTH1.html", markup)
        self.assertIn('rk.start(&quot;cpp-root-histogram&quot;)', markup)

    def test_intro_problem_is_generated_in_spanish_and_english(self):
        es = (ROOT / "docs" / "problems" / "cpp-hello-world.html").read_text(encoding="utf-8")
        en = (ROOT / "docs" / "en" / "problems" / "cpp-hello-world.html").read_text(encoding="utf-8")
        self.assertIn("Hola, mundo", es)
        self.assertIn("Introductorio", es)
        self.assertIn("Hello, world", en)
        self.assertIn("Introductory", en)

    def test_open_in_jupyter_targets_the_exact_generated_notebook(self):
        markup = (ROOT / "docs" / "problems" / "cpp-hello-world.html").read_text(encoding="utf-8")
        self.assertIn("http://127.0.0.1:8888/lab/tree/notebooks/cpp-hello-world.ipynb", markup)

    def test_language_switcher_keeps_the_same_page(self):
        es = (ROOT / "docs" / "problems" / "cpp-sum-positive.html").read_text(encoding="utf-8")
        self.assertIn('href="../en/problems/cpp-sum-positive.html"', es)
        en = (ROOT / "docs" / "en" / "problems" / "cpp-sum-positive.html").read_text(encoding="utf-8")
        self.assertIn('href="../../problems/cpp-sum-positive.html"', en)

    def test_nested_pages_reference_shared_assets_and_language_home(self):
        es_problem = (ROOT / "docs" / "problems" / "cpp-sum-positive.html").read_text(encoding="utf-8")
        self.assertIn('href="../styles.css"', es_problem)
        self.assertIn('src="../site.js"', es_problem)
        self.assertGreaterEqual(es_problem.count('href="../index.html"'), 2)
        self.assertNotIn('problems/styles.css', es_problem)

        en_index = (ROOT / "docs" / "en" / "index.html").read_text(encoding="utf-8")
        self.assertIn('href="../styles.css"', en_index)
        self.assertIn('src="../site.js"', en_index)
        self.assertIn('<a class="brand" href="index.html">ROOT Kata</a>', en_index)
        self.assertNotIn('href="en/styles.css"', en_index)

        en_problem = (ROOT / "docs" / "en" / "problems" / "cpp-sum-positive.html").read_text(encoding="utf-8")
        self.assertIn('href="../../styles.css"', en_problem)
        self.assertIn('src="../../site.js"', en_problem)
        self.assertGreaterEqual(en_problem.count('href="../index.html"'), 2)

    def test_authoring_templates_exist(self):
        self.assertTrue((ROOT / "docs" / "templates" / "problem.adoc").is_file())
        self.assertTrue((ROOT / "docs" / "templates" / "problem.md").is_file())


class DashboardTests(unittest.TestCase):
    def test_index_is_a_dashboard_with_progress_and_rows(self):
        markup = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
        self.assertIn('id="overall-progress"', markup)
        self.assertIn('id="progress-count"', markup)
        self.assertIn('id="badge-list"', markup)
        self.assertEqual(markup.count('class="kata-row"'), len(public_ids()))
        self.assertIn("Tu progreso", markup)

    def test_rows_carry_catalog_ids_for_localstorage_rendering(self):
        markup = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
        for eid in public_ids():
            self.assertIn(f'data-eid="{eid}"', markup)

    def test_english_dashboard_mirrors_spanish(self):
        markup = (ROOT / "docs" / "en" / "index.html").read_text(encoding="utf-8")
        self.assertIn("Your progress", markup)
        self.assertEqual(markup.count('class="kata-row"'), len(public_ids()))

    def test_site_js_absorbs_progress_params(self):
        js = (ROOT / "docs" / "site.js").read_text(encoding="utf-8")
        self.assertIn("absorbParams", js)
        self.assertIn("root-kata:solved", js)
        self.assertIn("root-kata:badges", js)

    def test_local_server_retargets_primary_actions_to_workspace(self):
        js = (ROOT / "docs" / "site.js").read_text(encoding="utf-8")
        self.assertIn("enableLocalWorkspace", js)
        self.assertIn("isLocalServe", js)
        self.assertIn("/kata/", js)
        self.assertIn("local-workspace-link", js)

    def test_dashboard_filters_by_difficulty(self):
        markup = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
        self.assertIn('id="difficulty-filter"', markup)
        self.assertIn('value="intermediate"', markup)
        self.assertIn('value="hard"', markup)
        self.assertEqual(markup.count('data-difficulty="intermediate"'), 3)
        self.assertEqual(markup.count('data-difficulty="hard"'), 3)

        js = (ROOT / "docs" / "site.js").read_text(encoding="utf-8")
        self.assertIn("renderDifficultyFilter", js)
        self.assertIn("row.dataset.difficulty", js)
        self.assertIn("row.hidden = !show", js)


if __name__ == "__main__":
    unittest.main()
