import sys
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from root_kata.catalog import get_exercise, list_exercises, localized

SHOWCASE_IDS = {
    "cpp-root-histogram-range",
    "cpp-root-tgraph-points",
    "cpp-root-tf1-evaluate",
    "cpp-root-histogram-selected-sample",
    "cpp-root-tf1-range-parameters",
    "cpp-root-fit-gaussian",
}


class ShowcaseKataTests(unittest.TestCase):
    def test_showcase_has_exact_requested_difficulty_mix(self):
        catalog = {item["id"]: item for item in list_exercises()}
        self.assertTrue(SHOWCASE_IDS <= catalog.keys())
        counts = Counter(catalog[eid]["difficulty"] for eid in SHOWCASE_IDS)
        self.assertEqual(counts, Counter({"Intermediate": 3, "Hard": 3}))

    def test_showcase_difficulties_are_localized(self):
        for eid in SHOWCASE_IDS:
            meta, _ = get_exercise(eid)
            expected = "Intermedio" if meta["difficulty"] == "Intermediate" else "Difícil"
            self.assertEqual(localized(meta, "es")["difficulty"], expected)

    def test_showcase_keeps_curriculum_provenance(self):
        for eid in SHOWCASE_IDS:
            meta, _ = get_exercise(eid)
            curriculum = meta["curriculum"]
            self.assertTrue(curriculum["competency"].strip())
            self.assertTrue(curriculum["observable_success"].strip())
            self.assertEqual(curriculum["source"]["repository"], "fbientrigo/root-student-course")


if __name__ == "__main__":
    unittest.main()
