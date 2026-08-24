import sys, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/"src"))
from root_kata.catalog import exercise_payload, list_exercises
class CatalogTests(unittest.TestCase):
    def test_catalog_contains_prototype_exercises(self): self.assertEqual({item["id"] for item in list_exercises()},{"cpp-sum-positive","cpp-count-above","cpp-root-histogram"})
    def test_payload_contains_starter_code(self): self.assertIn("int count_above",exercise_payload("cpp-count-above")["starter_code"])
    def test_public_catalog_is_ordered_learning_path(self): self.assertEqual([item["id"] for item in list_exercises()],["cpp-sum-positive","cpp-count-above","cpp-root-histogram"])
if __name__=="__main__": unittest.main()
