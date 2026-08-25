import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from root_kata.catalog import STARTER_PATH_IDS

PLAN = ROOT / "curriculum" / "plan.json"


class CurriculumPlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = json.loads(PLAN.read_text(encoding="utf-8"))

    def test_plan_has_one_active_current_milestone(self):
        current = self.plan["current_milestone"]
        active = [m for m in self.plan["milestones"] if m["status"] == "active"]
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0]["id"], current)

    def test_unit_and_target_ids_are_unique(self):
        unit_ids = []
        target_ids = []
        for milestone in self.plan["milestones"]:
            for unit in milestone.get("units", []):
                unit_ids.append(unit["id"])
                target_ids.extend(unit.get("target_exercises", []))
        self.assertEqual(len(unit_ids), len(set(unit_ids)))
        self.assertEqual(len(target_ids), len(set(target_ids)))
        self.assertFalse(set(target_ids) & set(STARTER_PATH_IDS))

    def test_prerequisites_follow_plan_order(self):
        available = set(STARTER_PATH_IDS)
        for milestone in self.plan["milestones"]:
            for unit in milestone.get("units", []):
                if unit["status"] == "deferred":
                    continue
                missing = set(unit["prerequisites"]) - available
                self.assertFalse(missing, f"{unit['id']} depends on future/unknown ids: {sorted(missing)}")
                available.update(unit.get("target_exercises", []))

    def test_planned_units_have_implementation_contract(self):
        allowed_transfer = {"introductory", "basic", "applied", "transfer", "challenge"}
        for milestone in self.plan["milestones"]:
            for unit in milestone.get("units", []):
                self.assertIn(unit["status"], self.plan["unit_statuses"])
                self.assertIn(unit["transfer_level"], allowed_transfer)
                if unit["status"] != "deferred":
                    self.assertTrue(unit["target_exercises"], unit["id"])
                    self.assertTrue(unit["competency"].strip(), unit["id"])
                    self.assertTrue(unit["acceptance"].strip(), unit["id"])
                    self.assertTrue(unit["source"]["path"].strip(), unit["id"])
                    self.assertTrue(unit["source"]["concept"].strip(), unit["id"])

    def test_source_baseline_is_pinned(self):
        source = self.plan["source_baseline"]
        self.assertEqual(source["repository"], "fbientrigo/root-student-course")
        self.assertRegex(source["ref"], r"^[0-9a-f]{40}$")


if __name__ == "__main__":
    unittest.main()
