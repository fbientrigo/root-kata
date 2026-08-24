import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_IDS = [
    "cpp-array-index",
    "cpp-array-print",
    "cpp-count-above",
    "cpp-hello-world",
    "cpp-root-histogram",
    "cpp-sum-positive",
]


class GitHubPagesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run([sys.executable, str(ROOT / "scripts" / "build_pages.py")], check=True, cwd=ROOT)

    def test_pages_publish_exactly_six_katas_per_language(self):
        for problems_dir in (ROOT / "docs" / "problems", ROOT / "docs" / "en" / "problems"):
            pages = sorted(problems_dir.glob("cpp-*.html"))
            self.assertEqual([p.stem for p in pages], EXPECTED_IDS)

    def test_spanish_is_primary_and_english_is_nested(self):
        self.assertTrue((ROOT / "docs" / "index.html").is_file())
        html_es = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
        html_en = (ROOT / "docs" / "en" / "index.html").read_text(encoding="utf-8")
        self.assertEqual(html_es.count("Abrir en Jupyter"), 7)  # 6 rows + local note
        self.assertEqual(html_en.count("Open in Jupyter"), 7)
        self.assertNotIn("/api/", html_es)
        self.assertIn('lang="es"', html_es)
        self.assertIn('lang="en"', html_en)
        self.assertIn("Introductorio", html_es)
        self.assertIn("Introductory", html_en)

    def test_problem_pages_link_references_and_use_stable_ids(self):
        html = (ROOT / "docs" / "problems" / "cpp-root-histogram.html").read_text(encoding="utf-8")
        self.assertIn("https://root.cern.ch/doc/master/classTH1.html", html)
        self.assertIn('rk.start(&quot;cpp-root-histogram&quot;)', html)

    def test_intro_problem_is_generated_in_spanish_and_english(self):
        es = (ROOT / "docs" / "problems" / "cpp-hello-world.html").read_text(encoding="utf-8")
        en = (ROOT / "docs" / "en" / "problems" / "cpp-hello-world.html").read_text(encoding="utf-8")
        self.assertIn("Hola, mundo", es)
        self.assertIn("Introductorio", es)
        self.assertIn("Hello, world", en)
        self.assertIn("Introductory", en)

    def test_open_in_jupyter_targets_the_exact_generated_notebook(self):
        html = (ROOT / "docs" / "problems" / "cpp-hello-world.html").read_text(encoding="utf-8")
        self.assertIn("http://127.0.0.1:8888/lab/tree/notebooks/cpp-hello-world.ipynb", html)

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
        html = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
        self.assertIn('id="overall-progress"', html)
        self.assertIn('id="progress-count"', html)
        self.assertIn('id="badge-list"', html)
        self.assertEqual(html.count('class="kata-row"'), 6)
        self.assertIn("Tu progreso", html)

    def test_rows_carry_stable_ids_for_localstorage_rendering(self):
        html = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
        for eid in ("cpp-hello-world", "cpp-array-index", "cpp-array-print", "cpp-sum-positive", "cpp-count-above", "cpp-root-histogram"):
            self.assertIn(f'data-eid="{eid}"', html)

    def test_english_dashboard_mirrors_spanish(self):
        html = (ROOT / "docs" / "en" / "index.html").read_text(encoding="utf-8")
        self.assertIn("Your progress", html)
        self.assertEqual(html.count('class="kata-row"'), 6)

    def test_site_js_absorbs_progress_params(self):
        js = (ROOT / "docs" / "site.js").read_text(encoding="utf-8")
        self.assertIn("absorbParams", js)
        self.assertIn("root-kata:solved", js)
        self.assertIn("root-kata:badges", js)


if __name__ == "__main__":
    unittest.main()
