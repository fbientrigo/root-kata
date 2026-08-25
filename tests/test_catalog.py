import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from root_kata.catalog import STARTER_PATH_IDS, exercise_payload, list_exercises, localized


class CatalogTests(unittest.TestCase):
    def test_catalog_preserves_starter_path_prefix(self):
        ids = [item["id"] for item in list_exercises()]
        self.assertEqual(ids[:len(STARTER_PATH_IDS)], list(STARTER_PATH_IDS))

    def test_catalog_ids_are_unique(self):
        ids = [item["id"] for item in list_exercises(include_unpublished=True)]
        self.assertEqual(len(ids), len(set(ids)))

    def test_payload_contains_starter_code(self):
        self.assertIn("int count_above", exercise_payload("cpp-count-above")["starter_code"])
        self.assertIn("void say_hello", exercise_payload("cpp-hello-world")["starter_code"])

    def test_introductory_difficulty_is_localized(self):
        hello = exercise_payload("cpp-hello-world")
        self.assertEqual(localized(hello, "es")["difficulty"], "Introductorio")
        self.assertEqual(localized(hello, "en")["difficulty"], "Introductory")

    def test_histogram_preview_metadata_is_accepted_and_localized(self):
        from root_kata.catalog import get_exercise
        meta, _ = get_exercise("cpp-root-histogram")
        self.assertEqual(localized(meta, "en")["preview"], {"file": "preview.png", "alt": "Histogram produced by your code"})
        self.assertEqual(localized(meta, "es")["preview"], {"file": "preview.png", "alt": "Histograma generado por tu código"})

    def test_exercises_without_preview_metadata_remain_valid(self):
        from root_kata.catalog import get_exercise
        meta, _ = get_exercise("cpp-sum-positive")
        self.assertNotIn("preview", meta)


class CurriculumContractTests(unittest.TestCase):
    def _write_exercise(self, root: Path, exercise_id: str, curriculum=None) -> None:
        directory = root / exercise_id
        directory.mkdir(parents=True)
        meta = {
            "id": exercise_id,
            "kind": "cpp",
            "title": "Synthetic kata",
            "track": "Synthetic",
            "difficulty": "Easy",
            "summary": "Synthetic exercise for contract validation.",
            "description": "Implement int answer().",
            "requirements": ["Return 42."],
            "entrypoint": "answer",
            "starter": "solution.cpp",
            "harness": "harness.cpp",
            "validator": "validator.py",
            "requires": [],
        }
        if curriculum is not None:
            meta["curriculum"] = curriculum
        (directory / "exercise.json").write_text(json.dumps(meta), encoding="utf-8")
        (directory / "solution.cpp").write_text("int answer(){return 0;}\n", encoding="utf-8")

    def _valid_curriculum(self, prerequisites=None):
        return {
            "competency": "Choose and implement a previously learned operation in a changed context.",
            "prerequisites": list(prerequisites or []),
            "transfer_level": "applied",
            "misconception": "The learner copies syntax without adapting the operation to the data.",
            "observable_success": "The submitted function returns the expected result for changed inputs.",
            "source": {
                "repository": "fbientrigo/root-student-course",
                "path": "course/notebooks/core/01-histograms-and-graphs.ipynb",
                "concept": "histogram construction and inspection",
            },
        }

    def test_new_exercise_requires_curriculum_metadata(self):
        with tempfile.TemporaryDirectory() as t:
            self._write_exercise(Path(t), "future-kata")
            with mock.patch.dict(os.environ, {"ROOT_KATA_EXERCISES": t}):
                with self.assertRaisesRegex(ValueError, "curriculum"):
                    list_exercises()

    def test_valid_curriculum_metadata_is_accepted(self):
        with tempfile.TemporaryDirectory() as t:
            self._write_exercise(Path(t), "future-kata", self._valid_curriculum())
            with mock.patch.dict(os.environ, {"ROOT_KATA_EXERCISES": t}):
                self.assertEqual([item["id"] for item in list_exercises()], ["future-kata"])

    def test_unknown_transfer_level_is_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            curriculum = self._valid_curriculum()
            curriculum["transfer_level"] = "harder-because-longer"
            self._write_exercise(Path(t), "future-kata", curriculum)
            with mock.patch.dict(os.environ, {"ROOT_KATA_EXERCISES": t}):
                with self.assertRaisesRegex(ValueError, "transfer_level"):
                    list_exercises()

    def test_unknown_prerequisite_is_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            self._write_exercise(Path(t), "future-kata", self._valid_curriculum(["missing-kata"]))
            with mock.patch.dict(os.environ, {"ROOT_KATA_EXERCISES": t}):
                with self.assertRaisesRegex(ValueError, "unknown curriculum prerequisite"):
                    list_exercises()


if __name__ == "__main__":
    unittest.main()
