import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from root_kata.cpp_runner import _which_compiler, run_cpp

HELLO = '''#include <iostream>\nvoid say_hello(){std::cout << "Hello, world!" << std::endl;}\n'''
ARRAY_INDEX = '''int second_value(){int values[3]={10,20,30};return values[1];}\n'''
ARRAY_PRINT = '''#include <iostream>\nvoid print_values(){int values[3]={4,8,15};for(int value:values)std::cout << value << ' ';}\n'''


@unittest.skipIf(_which_compiler() is None, "no C++ compiler")
class IntroCurriculumTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_code(self, exercise_id, code):
        src = self.tmp / f"{exercise_id}.cpp"
        src.write_text(code, encoding="utf-8")
        return run_cpp(exercise_id, src, work=self.tmp / f"work-{exercise_id}")

    def test_hello_world_reference_passes(self):
        result = self.run_code("cpp-hello-world", HELLO)
        self.assertEqual(result["status"], "passed", result)
        self.assertEqual(len(result["cases"]), 2)

    def test_array_index_reference_passes(self):
        result = self.run_code("cpp-array-index", ARRAY_INDEX)
        self.assertEqual(result["status"], "passed", result)
        self.assertEqual(len(result["cases"]), 1)

    def test_array_print_reference_passes(self):
        result = self.run_code("cpp-array-print", ARRAY_PRINT)
        self.assertEqual(result["status"], "passed", result)
        self.assertEqual(len(result["cases"]), 4)


if __name__ == "__main__":
    unittest.main()
