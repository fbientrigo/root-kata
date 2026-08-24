import importlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import root_kata.i18n as i18n


def with_home(fn):
    """Run with an isolated ROOT_KATA_HOME."""
    def wrapper(*a, **kw):
        with tempfile.TemporaryDirectory() as t, mock.patch.dict(os.environ, {"ROOT_KATA_HOME": t}):
            return fn(*a, **kw)
    return wrapper


class LanguageResolutionTests(unittest.TestCase):
    @with_home
    def test_default_is_spanish(self):
        self.assertEqual(i18n.get_lang(), "es")

    @with_home
    def test_env_overrides_config(self):
        i18n.set_lang("en")
        self.assertEqual(i18n.get_lang(), "en")
        with mock.patch.dict(os.environ, {"ROOT_KATA_LANG": "es"}):
            self.assertEqual(i18n.get_lang(), "es")

    @with_home
    def test_set_lang_persists_and_validates(self):
        i18n.set_lang("en")
        stored = json.loads((Path(os.environ["ROOT_KATA_HOME"]) / "config.json").read_text())
        self.assertEqual(stored["language"], "en")
        with self.assertRaises(ValueError):
            i18n.set_lang("fr")

    @with_home
    def test_unknown_keys_fall_back_to_key(self):
        self.assertEqual(i18n.t("no.such.key"), "no.such.key")

    @with_home
    def test_every_es_key_exists_in_en(self):
        missing = set(i18n._STRINGS["es"]) ^ set(i18n._STRINGS["en"])
        self.assertEqual(missing, set())


class BadgeLabelTests(unittest.TestCase):
    @with_home
    def test_badge_names_are_localized_from_stable_ids(self):
        from root_kata.catalog import badge_label
        self.assertEqual(badge_label("first_kata"), "Primer kata")
        with mock.patch.dict(os.environ, {"ROOT_KATA_LANG": "en"}):
            self.assertEqual(badge_label("first_kata"), "First Kata")


if __name__ == "__main__":
    unittest.main()
