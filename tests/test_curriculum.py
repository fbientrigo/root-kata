import shutil,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
from root_kata.cpp_runner import _which_compiler,run_cpp
GOOD_COUNT='''#include <vector>\nint count_above(const std::vector<double>& values,double threshold){int count=0;for(double value:values)if(value>threshold)++count;return count;}\n'''
WRONG_BOUNDARY='''#include <vector>\nint count_above(const std::vector<double>& values,double threshold){int count=0;for(double value:values)if(value>=threshold)++count;return count;}\n'''
@unittest.skipIf(_which_compiler() is None,"no C++ compiler")
class StarterCurriculumTests(unittest.TestCase):
    def setUp(self):self.tmp=Path(tempfile.mkdtemp())
    def tearDown(self):shutil.rmtree(self.tmp,ignore_errors=True)
    def run_count(self,code):
        src=self.tmp/"solution.cpp";src.write_text(code,encoding="utf-8");return run_cpp("cpp-count-above",src,work=self.tmp/"work")
    def test_count_above_reference_shape_passes_all_visible_cases(self):
        result=self.run_count(GOOD_COUNT);self.assertEqual(result["status"],"passed",result);self.assertEqual(len(result["cases"]),4)
    def test_count_above_exposes_strict_boundary_error(self):
        result=self.run_count(WRONG_BOUNDARY);self.assertEqual(result["status"],"failed");failed={case["name"] for case in result["cases"] if not case["passed"]};self.assertIn("strict boundary",failed)
if __name__=="__main__":unittest.main()
