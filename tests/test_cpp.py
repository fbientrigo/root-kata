import sys,tempfile,unittest,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
from root_kata.cpp_runner import run_cpp,_which_compiler
GOOD="#include <vector>\ndouble sum_positive(const std::vector<double>& v){double s=0;for(double x:v) if(x>0) s+=x;return s;}\n";WRONG="#include <vector>\ndouble sum_positive(const std::vector<double>& v){double s=0;for(double x:v) s+=x;return s;}\n";BROKEN="#include <vector>\ndouble sum_positive(const std::vector<double>& v){double s=0;for(double x:v) if(x>0) s+=x;return s\n}\n";CRASH="#include <vector>\ndouble sum_positive(const std::vector<double>& v){int* p=nullptr;return *p;}\n";LOOP="#include <vector>\ndouble sum_positive(const std::vector<double>& v){while(true){}return 0;}\n"
@unittest.skipIf(_which_compiler() is None,"no C++ compiler")
class CppRunnerTests(unittest.TestCase):
    def setUp(self):self.tmp=Path(tempfile.mkdtemp())
    def tearDown(self):shutil.rmtree(self.tmp,ignore_errors=True)
    def _run(self,code,**kw):src=self.tmp/"solution.cpp";src.write_text(code);return run_cpp("cpp-sum-positive",src,work=self.tmp/"work",**kw)
    def test_pass(self):
        r=self._run(GOOD);self.assertEqual(r["status"],"passed",r);self.assertEqual(len(r["cases"]),4);self.assertTrue((self.tmp/"work"/"compile.sh").exists())
    def test_wrong_answer_reports_expected_actual(self):
        r=self._run(WRONG);self.assertEqual(r["status"],"failed");bad=[c for c in r["cases"] if not c["passed"]];self.assertTrue(bad and bad[0]["expected"] is not None)
    def test_compile_error_points_at_student_line(self):
        r=self._run(BROKEN);self.assertEqual(r["status"],"compile_error");self.assertEqual(r["first_error"]["file"],"solution.cpp");self.assertTrue(r["first_error"]["in_student_file"]);self.assertIn("solution.cpp",r["summary"])
    def test_crash(self):
        r=self._run(CRASH);self.assertEqual(r["status"],"runtime_error");self.assertIn("SIGSEGV",r["summary"])
    def test_timeout(self):
        r=self._run(LOOP,timeout_seconds=.5);self.assertEqual(r["status"],"runtime_error");self.assertIn("longer",r["summary"])
if __name__=="__main__":unittest.main()
