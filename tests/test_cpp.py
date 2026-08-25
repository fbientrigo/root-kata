import shutil,sys,tempfile,unittest
from pathlib import Path
from unittest import mock
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
from root_kata.cpp_runner import run_cpp,_which_compiler,root_config_flags
def _has_root():return root_config_flags() is not None
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


@unittest.skipIf(_which_compiler() is None,"no C++ compiler")
class PreviewArtifactLifecycleTests(unittest.TestCase):
    """Stale-preview invariant against a fake exercise, so this needs g++ but not ROOT."""
    def setUp(self):
        self.tmp=Path(tempfile.mkdtemp())
        self.ex_dir=self.tmp/"exercise";self.ex_dir.mkdir()
        (self.ex_dir/"harness.cpp").write_text(
            '#include "rk.h"\n#include "solution.cpp"\n#include <fstream>\n'
            'int main(){bool ok=should_preview();rk::emit("ok",ok);'
            'if(ok){std::ofstream f("preview.png");f<<"PNGDATA";}return rk::done();}\n')
        (self.ex_dir/"validator.py").write_text(
            "from root_kata.validation import case, expect\n"
            "def grade(r): return [case('ok', lambda: expect(r.get('ok'), 'should be ok'))]\n")
        self.metadata={"harness":"harness.cpp","starter":"solution.cpp","validator":"validator.py","requires":[],
                       "preview":{"file":"preview.png","alt":"x"}}
    def tearDown(self):shutil.rmtree(self.tmp,ignore_errors=True)
    def _run(self,code,work):
        src=self.tmp/"solution.cpp";src.write_text(code)
        with mock.patch("root_kata.cpp_runner.get_exercise",return_value=(self.metadata,self.ex_dir)):
            return run_cpp("fake-preview-exercise",src,work=work)
    def test_run_that_produces_preview_exposes_its_path(self):
        r=self._run("bool should_preview(){return true;}\n",self.tmp/"work")
        self.assertEqual(r["status"],"passed");self.assertTrue(Path(r["preview"]["path"]).is_file())
    def test_run_that_does_not_produce_preview_exposes_nothing(self):
        r=self._run("bool should_preview(){return false;}\n",self.tmp/"work")
        self.assertIn(r["status"],("passed","failed"));self.assertNotIn("preview",r)
    def test_stale_preview_from_a_prior_attempt_is_never_reused(self):
        work=self.tmp/"work"
        first=self._run("bool should_preview(){return true;}\n",work);self.assertIn("preview",first)
        second=self._run("bool should_preview(){return false;}\n",work)
        self.assertNotIn("preview",second);self.assertFalse((work/"preview.png").exists())
    def test_compile_error_never_exposes_a_stale_preview(self):
        work=self.tmp/"work"
        first=self._run("bool should_preview(){return true;}\n",work);self.assertIn("preview",first)
        second=self._run("bool should_preview(){return true\n",work)  # syntax error
        self.assertEqual(second["status"],"compile_error")
        self.assertNotIn("preview",second);self.assertFalse((work/"preview.png").exists())


@unittest.skipUnless(_which_compiler() and _has_root(),"no C++ compiler or ROOT")
class RootHistogramPreviewIntegrationTests(unittest.TestCase):
    GOOD='#include <vector>\n#include "TH1D.h"\nTH1D* build_histogram(const std::vector<double>& values){TH1D* h=new TH1D("h_pt","h_pt",10,0,100);for(double v:values)h->Fill(v);return h;}\n'
    WRONG_BINS='#include <vector>\n#include "TH1D.h"\nTH1D* build_histogram(const std::vector<double>& values){TH1D* h=new TH1D("h_pt","h_pt",5,0,100);for(double v:values)h->Fill(v);return h;}\n'
    def setUp(self):self.tmp=Path(tempfile.mkdtemp())
    def tearDown(self):shutil.rmtree(self.tmp,ignore_errors=True)
    def _run(self,code,work):
        src=self.tmp/"solution.cpp";src.write_text(code)
        return run_cpp("cpp-root-histogram",src,work=work)
    def test_correct_solution_compiles_runs_and_produces_a_nonempty_preview(self):
        r=self._run(self.GOOD,self.tmp/"work")
        self.assertEqual(r["status"],"passed");self.assertEqual(len(r["cases"]),3)
        self.assertTrue(all(c["passed"] for c in r["cases"]))
        preview=Path(r["preview"]["path"]);self.assertTrue(preview.is_file());self.assertGreater(preview.stat().st_size,0)
    def test_wrong_binning_fails_grading_but_still_shows_the_current_preview(self):
        r=self._run(self.WRONG_BINS,self.tmp/"work")
        self.assertEqual(r["status"],"failed")
        self.assertTrue(Path(r["preview"]["path"]).is_file())
    def test_changing_binning_visibly_changes_the_next_preview(self):
        work=self.tmp/"work"
        first=self._run(self.GOOD,work);first_bytes=Path(first["preview"]["path"]).read_bytes()
        second=self._run(self.WRONG_BINS,work);second_bytes=Path(second["preview"]["path"]).read_bytes()
        self.assertNotEqual(first_bytes,second_bytes)


if __name__=="__main__":unittest.main()
