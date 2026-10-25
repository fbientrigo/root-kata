"""Guard the two-language Observatory design during Pages regeneration."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


class ObservatoryDesignTests(unittest.TestCase):
    def test_shared_asset_is_shipped(self):
        css = (DOCS / "observatory.css").read_text(encoding="utf-8")
        self.assertIn("--rk-font-display", css)
        self.assertIn(".field-visual", css)
        self.assertIn("prefers-reduced-motion", css)
        self.assertNotIn("http://127.0.0.1", css)

    def test_bilingual_home_preserves_controls_and_decorative_art(self):
        for lang, path, asset in (
            ("es", DOCS / "index.html", 'href="observatory.css"'),
            ("en", DOCS / "en" / "index.html", 'href="../observatory.css"'),
        ):
            with self.subTest(lang=lang):
                html = path.read_text(encoding="utf-8")
                self.assertIn(asset, html)
                self.assertIn('class="hero-copy"', html)
                self.assertIn('class="field-visual"', html)
                self.assertIn('aria-hidden="true"', html)
                self.assertIn('class="progress-panel"', html)
                self.assertIn('id="difficulty-filter"', html)
                self.assertIn('class="kata-list"', html)

    def test_browser_editor_uses_shared_skin_without_touching_evaluator(self):
        for lang, path, asset in (
            ("es", DOCS / "solve" / "cpp-root-histogram.html", 'href="../observatory.css"'),
            ("en", DOCS / "en" / "solve" / "cpp-root-histogram.html", 'href="../../observatory.css"'),
        ):
            with self.subTest(lang=lang):
                html = path.read_text(encoding="utf-8")
                self.assertIn(asset, html)
                self.assertIn('id="run-button"', html)
                self.assertIn('id="code-editor"', html)
                self.assertIn('id="run-feedback"', html)


if __name__ == "__main__":
    unittest.main()
