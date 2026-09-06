import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "docs" / "quick-reference.json"
TOPICS = ROOT / "docs" / "quick-reference-topics.json"


class QuickReferenceTopicTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = json.loads(BASE.read_text(encoding="utf-8"))
        cls.topics = json.loads(TOPICS.read_text(encoding="utf-8"))

    def test_every_domain_has_one_deep_topic(self):
        domain_ids = [domain["id"] for domain in self.base["domains"]]
        topic_ids = [topic["id"] for topic in self.topics["topics"]]
        self.assertEqual(topic_ids, domain_ids)

    def test_deep_topics_are_learning_content_not_duplicate_snippets(self):
        for topic in self.topics["topics"]:
            self.assertTrue(topic["summary"])
            self.assertTrue(topic["mental_model"])
            self.assertGreaterEqual(len(topic["workflow"]), 4)
            self.assertGreaterEqual(len(topic["recipes"]), 2)
            self.assertGreaterEqual(len(topic["pitfalls"]), 3)
            for recipe in topic["recipes"]:
                self.assertTrue(recipe["title"])
                self.assertTrue(recipe["python"])
                self.assertTrue(recipe["cpp"])
            for doc in topic["docs"]:
                self.assertTrue(doc["url"].startswith("https://root.cern/"))

    def test_deep_view_assets_exist(self):
        for path in (
            "docs/quick-reference-topic.html",
            "docs/quick-reference-topic.js",
            "docs/quick-reference-depth.css",
        ):
            self.assertTrue((ROOT / path).is_file(), path)


if __name__ == "__main__":
    unittest.main()
