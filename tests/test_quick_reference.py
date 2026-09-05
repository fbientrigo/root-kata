import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs" / "quick-reference.json"


class QuickReferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = json.loads(DATA.read_text(encoding="utf-8"))

    def test_reference_has_compact_intent_domains(self):
        domains = self.payload["domains"]
        self.assertEqual(
            [domain["id"] for domain in domains],
            ["files", "histograms", "rdataframe", "trees", "fits", "plotting"],
        )
        for domain in domains:
            self.assertGreaterEqual(len(domain["items"]), 5)
            self.assertLessEqual(len(domain["items"]), 8)

    def test_entries_are_complete_and_ids_unique(self):
        ids = []
        for domain in self.payload["domains"]:
            for item in domain["items"]:
                ids.append(item["id"])
                for field in ("intent", "aliases", "python", "cpp"):
                    self.assertTrue(item.get(field), f"{item['id']} is missing {field}")
                if item.get("docs"):
                    self.assertTrue(item["docs"].startswith("https://root.cern/"))
                if item.get("kata"):
                    self.assertTrue((ROOT / "docs" / item["kata"]).is_file())
        self.assertEqual(len(ids), len(set(ids)))

    def test_acceptance_queries_have_explicit_search_vocabulary(self):
        text = " ".join(
            " ".join([domain["label"], item["intent"], *item.get("aliases", [])]).lower()
            for domain in self.payload["domains"]
            for item in domain["items"]
        )
        for phrase in (
            "read root file",
            "get bin 4",
            "normalize histogram",
            "filter events",
            "create derived variable",
            "fit gaussian",
            "save plot",
        ):
            self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
