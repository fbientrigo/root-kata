import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class GitHubPagesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run([sys.executable, str(ROOT / "scripts" / "build_pages.py")], check=True, cwd=ROOT)

    def test_pages_publish_exactly_three_katas(self):
        pages = sorted((ROOT / "docs" / "problems").glob("cpp-*.html"))
        self.assertEqual([p.stem for p in pages], ["cpp-count-above", "cpp-root-histogram", "cpp-sum-positive"])

    def test_index_is_static_and_jupyter_first(self):
        html = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
        self.assertEqual(html.count("Open in Jupyter"), 4)
        self.assertNotIn("/api/", html)
        self.assertIn("http://127.0.0.1:8888/lab", html)

    def test_problem_pages_link_markdown_and_references(self):
        html = (ROOT / "docs" / "problems" / "cpp-root-histogram.html").read_text(encoding="utf-8")
        self.assertIn("Markdown problem source", html)
        self.assertIn("https://root.cern.ch/doc/master/classTH1.html", html)
        self.assertIn('rk.start(&quot;cpp-root-histogram&quot;)', html)

    def test_authoring_templates_exist(self):
        self.assertTrue((ROOT / "docs" / "templates" / "problem.adoc").is_file())
        self.assertTrue((ROOT / "docs" / "templates" / "problem.md").is_file())

if __name__ == "__main__": unittest.main()
