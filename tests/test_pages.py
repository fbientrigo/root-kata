import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class GitHubPagesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run([sys.executable, str(ROOT / "scripts" / "build_pages.py")], check=True, cwd=ROOT)

    def test_pages_publish_exactly_three_katas_per_language(self):
        for problems_dir in (ROOT / "docs" / "problems", ROOT / "docs" / "en" / "problems"):
            pages = sorted(problems_dir.glob("cpp-*.html"))
            self.assertEqual([p.stem for p in pages], ["cpp-count-above", "cpp-root-histogram", "cpp-sum-positive"])

    def test_spanish_is_primary_and_english_is_nested(self):
        self.assertTrue((ROOT / "docs" / "index.html").is_file())
        html_es = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
        self.assertEqual(html_es.count("Abrir en Jupyter"), 4)  # 3 cards + local note
        html_en = (ROOT / "docs" / "en" / "index.html").read_text(encoding="utf-8")
        self.assertEqual(html_en.count("Open in Jupyter"), 4)  # 3 cards + local note
        self.assertNotIn("/api/", html_es)
        self.assertIn('lang="es"', html_es)
        self.assertIn('lang="en"', html_en)

    def test_problem_pages_link_references_and_use_stable_ids(self):
        html = (ROOT / "docs" / "problems" / "cpp-root-histogram.html").read_text(encoding="utf-8")
        self.assertIn("https://root.cern.ch/doc/master/classTH1.html", html)
        self.assertIn('rk.start(&quot;cpp-root-histogram&quot;)', html)

    def test_open_in_jupyter_targets_the_exact_generated_notebook(self):
        html = (ROOT / "docs" / "problems" / "cpp-sum-positive.html").read_text(encoding="utf-8")
        self.assertIn("http://127.0.0.1:8888/lab/tree/notebooks/cpp-sum-positive.ipynb", html)

    def test_language_switcher_keeps_the_same_page(self):
        es = (ROOT / "docs" / "problems" / "cpp-sum-positive.html").read_text(encoding="utf-8")
        self.assertIn('href="../en/problems/cpp-sum-positive.html"', es)
        en = (ROOT / "docs" / "en" / "problems" / "cpp-sum-positive.html").read_text(encoding="utf-8")
        self.assertIn('href="../../problems/cpp-sum-positive.html"', en)

    def test_authoring_templates_exist(self):
        self.assertTrue((ROOT / "docs" / "templates" / "problem.adoc").is_file())
        self.assertTrue((ROOT / "docs" / "templates" / "problem.md").is_file())


if __name__ == "__main__":
    unittest.main()


class DashboardTests(unittest.TestCase):
    def test_index_is_a_dashboard_with_progress_and_rows(self):
        html = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
        self.assertIn('id="overall-progress"', html)
        self.assertIn('id="progress-count"', html)
        self.assertIn('id="badge-list"', html)
        self.assertEqual(html.count('class="kata-row"'), 3)
        self.assertIn("Tu progreso", html)

    def test_rows_carry_stable_ids_for_localstorage_rendering(self):
        html = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
        for eid in ("cpp-sum-positive", "cpp-count-above", "cpp-root-histogram"):
            self.assertIn(f'data-eid="{eid}"', html)

    def test_english_dashboard_mirrors_spanish(self):
        html = (ROOT / "docs" / "en" / "index.html").read_text(encoding="utf-8")
        self.assertIn("Your progress", html)
        self.assertEqual(html.count('class="kata-row"'), 3)

    def test_site_js_absorbs_progress_params(self):
        js = (ROOT / "docs" / "site.js").read_text(encoding="utf-8")
        self.assertIn("absorbParams", js)
        self.assertIn("root-kata:solved", js)
        self.assertIn("root-kata:badges", js)
