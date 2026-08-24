import sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from root_kata.catalog import exercise_payload, list_exercises, localized

EXPECTED_IDS = [
    "cpp-hello-world",
    "cpp-array-index",
    "cpp-array-print",
    "cpp-sum-positive",
    "cpp-count-above",
    "cpp-root-histogram",
]


class CatalogTests(unittest.TestCase):
    def test_catalog_contains_public_learning_path(self):
        self.assertEqual({item["id"] for item in list_exercises()}, set(EXPECTED_IDS))

    def test_payload_contains_starter_code(self):
        self.assertIn("int count_above", exercise_payload("cpp-count-above")["starter_code"])
        self.assertIn("void say_hello", exercise_payload("cpp-hello-world")["starter_code"])

    def test_public_catalog_is_ordered_from_zero_to_root(self):
        self.assertEqual([item["id"] for item in list_exercises()], EXPECTED_IDS)

    def test_introductory_difficulty_is_localized(self):
        hello = exercise_payload("cpp-hello-world")
        self.assertEqual(localized(hello, "es")["difficulty"], "Introductorio")
        self.assertEqual(localized(hello, "en")["difficulty"], "Introductory")


if __name__ == "__main__":
    unittest.main()
