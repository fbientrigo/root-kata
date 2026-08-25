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

# `root_kata.progress` is shadowed by a public function of the same name;
# reach the module through sys.modules.
importlib.import_module("root_kata.progress")
progress = sys.modules["root_kata.progress"]


class ProgressMigrationTests(unittest.TestCase):
    def _run(self, badges):
        with tempfile.TemporaryDirectory() as t, mock.patch.dict(os.environ, {"ROOT_KATA_HOME": t}):
            (Path(t) / "progress.json").write_text(json.dumps({
                "solved": {"cpp-sum-positive": {"at": "2026-01-01T00:00:00", "attempts": 2, "first_try": False}},
                "attempts": {"cpp-sum-positive": 2},
                "badges": badges,
            }), encoding="utf-8")
            data = progress.load()
        return data

    def test_legacy_badge_names_map_to_stable_ids(self):
        data = self._run({"First Kata": "2026-01-01T00:00:00", "Histogrammer": "2026-01-02T00:00:00"})
        self.assertEqual(set(data["badges"]), {"first_kata", "first_root_histogram"})
        self.assertEqual(data["badges"]["first_kata"], "2026-01-01T00:00:00")

    def test_retired_badges_are_dropped(self):
        data = self._run({"Clean Shot": "2026-01-01T00:00:00", "Completionist": "2026-01-01T00:00:00"})
        self.assertEqual(data["badges"], {"basics_complete": "2026-01-01T00:00:00"})

    def test_solving_is_language_independent_and_earns_stable_ids(self):
        with tempfile.TemporaryDirectory() as t, mock.patch.dict(os.environ, {"ROOT_KATA_HOME": t}):
            for lang in ("es", "en"):
                progress.record("cpp-hello-world", {"passed": True})
                data = progress.load()
                self.assertTrue(data["solved"]["cpp-hello-world"])
                self.assertIn("first_kata", data["badges"])
                self.assertNotIn("Primer kata", json.dumps(data))
                self.assertNotIn("First Kata", json.dumps(data))
            self.assertEqual(progress.load()["badges"]["first_kata"].count("T"), 1)

    def test_first_attempt_no_longer_grants_a_badge(self):
        with tempfile.TemporaryDirectory() as t, mock.patch.dict(os.environ, {"ROOT_KATA_HOME": t}):
            progress.record("cpp-hello-world", {"passed": True})
            self.assertNotIn("Clean Shot", progress.load()["badges"])

    def test_basics_complete_requires_starter_path(self):
        ids = progress.STARTER_PATH_IDS
        with tempfile.TemporaryDirectory() as t, mock.patch.dict(os.environ, {"ROOT_KATA_HOME": t}):
            for eid in ids[:-1]:
                progress.record(eid, {"passed": True})
            self.assertNotIn("basics_complete", progress.load()["badges"])
            progress.record(ids[-1], {"passed": True})
            self.assertIn("basics_complete", progress.load()["badges"])

    def test_future_catalog_growth_does_not_move_basics_goalpost(self):
        catalog = [{"id": eid} for eid in progress.STARTER_PATH_IDS] + [{"id": "future-rdataframe-kata"}]
        with tempfile.TemporaryDirectory() as t, mock.patch.dict(os.environ, {"ROOT_KATA_HOME": t}), mock.patch.object(progress, "list_exercises", return_value=catalog):
            for eid in progress.STARTER_PATH_IDS:
                progress.record(eid, {"passed": True})
            self.assertIn("basics_complete", progress.load()["badges"])
            self.assertNotIn("future-rdataframe-kata", progress.load()["solved"])


if __name__ == "__main__":
    unittest.main()
