import csv
import json
import sys
import unittest
from collections import OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from root_kata.catalog import STARTER_PATH_IDS

PLAN = ROOT / "curriculum" / "plan.json"
TRIADS = ROOT / "curriculum" / "triads"
CORE_MILESTONES = [
    "m1-histograms-modeling",
    "m2-files-datasets",
    "m3-rdataframe-essentials",
    "m4-rvec-object-selection",
    "m5-analysis-workflows",
    "m6-analysis-transfer",
]
ROLES = ["normal", "limitation", "integration"]
ALLOWED_STATUS = {"planned", "implemented", "blocked"}
ALLOWED_TRANSFER = {"introductory", "basic", "applied", "transfer", "challenge"}


def load_rows(milestone):
    path = TRIADS / f"{milestone}.csv"
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


class CurriculumTriadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = json.loads(PLAN.read_text(encoding="utf-8"))
        cls.rows = {mid: load_rows(mid) for mid in CORE_MILESTONES}

    def test_current_milestone_has_exercise_queue(self):
        current = self.plan["current_milestone"]
        self.assertIn(current, CORE_MILESTONES)
        self.assertTrue((TRIADS / f"{current}.csv").is_file())

    def test_each_theme_is_use_limitation_integration(self):
        for milestone, rows in self.rows.items():
            themes = OrderedDict()
            for row in rows:
                themes.setdefault(row["theme"], []).append(row["role"])
            self.assertTrue(themes, milestone)
            for theme, roles in themes.items():
                self.assertEqual(roles, ROLES, f"{milestone}/{theme}: {roles}")

    def test_exercise_ids_are_unique_and_not_starter_ids(self):
        ids = [row["exercise_id"] for rows in self.rows.values() for row in rows]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertFalse(set(ids) & set(STARTER_PATH_IDS))

    def test_prerequisites_follow_exercise_order(self):
        available = set(STARTER_PATH_IDS)
        for milestone in CORE_MILESTONES:
            for row in self.rows[milestone]:
                prerequisites = {p for p in row["prerequisites"].split("|") if p}
                missing = prerequisites - available
                self.assertFalse(
                    missing,
                    f"{milestone}/{row['exercise_id']} depends on future/unknown ids: {sorted(missing)}",
                )
                available.add(row["exercise_id"])

    def test_rows_have_execution_contract(self):
        for milestone, rows in self.rows.items():
            for row in rows:
                label = f"{milestone}/{row['exercise_id']}"
                self.assertIn(row["role"], ROLES, label)
                self.assertIn(row["status"], ALLOWED_STATUS, label)
                self.assertIn(row["transfer_level"], ALLOWED_TRANSFER, label)
                self.assertTrue(row["source_path"].strip(), label)
                self.assertTrue(row["source_concept"].strip(), label)
                self.assertTrue(row["competency"].strip(), label)
                self.assertTrue(row["acceptance"].strip(), label)
                self.assertIn(row["requires_real_root"], {"true", "false"}, label)

    def test_limitation_and_integration_are_not_cosmetic_duplicates(self):
        for milestone, rows in self.rows.items():
            by_theme = OrderedDict()
            for row in rows:
                by_theme.setdefault(row["theme"], []).append(row)
            for theme, sequence in by_theme.items():
                goals = [row["competency"].strip().lower() for row in sequence]
                self.assertEqual(len(goals), len(set(goals)), f"duplicate competency in {milestone}/{theme}")
                self.assertNotEqual(sequence[0]["exercise_id"], sequence[1]["exercise_id"])
                self.assertNotEqual(sequence[1]["exercise_id"], sequence[2]["exercise_id"])


if __name__ == "__main__":
    unittest.main()
