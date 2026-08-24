import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from root_kata import lab as lab_mod
from root_kata.catalog import list_exercises


class StarterNotebookTests(unittest.TestCase):
    def test_notebook_is_valid_and_opens_the_exact_kata(self):
        nb = lab_mod.starter_notebook("cpp-sum-positive")
        self.assertEqual(nb["nbformat"], 4)
        source = "".join(nb["cells"][0]["source"])
        self.assertIn("import root_kata as rk", source)
        self.assertIn('rk.start("cpp-sum-positive")', source)

    def test_ensure_creates_one_bootstrap_notebook_per_exercise(self):
        with tempfile.TemporaryDirectory() as t:
            written = lab_mod.ensure_notebooks(Path(t))
            expected = {f"{ex['id']}.ipynb" for ex in list_exercises()}
            self.assertEqual({p.name for p in written}, expected)
            for p in written:
                json.loads(p.read_text(encoding="utf-8"))
            self.assertEqual(lab_mod.ensure_notebooks(Path(t)), [])


class LabCommandTests(unittest.TestCase):
    def test_lab_runs_this_interpreter_jupyterlab_without_browser(self):
        captured = {}

        def fake_run(cmd, **kw):
            captured["cmd"] = cmd
            return mock.Mock(returncode=0)

        with tempfile.TemporaryDirectory() as t, \
                mock.patch.dict("os.environ", {"ROOT_KATA_NOTEBOOKS": t}), \
                mock.patch.object(lab_mod.subprocess, "run", side_effect=fake_run):
            code = lab_mod.lab(port=9001)
        self.assertEqual(code, 0)
        cmd = captured["cmd"]
        self.assertEqual(cmd[0], sys.executable)
        self.assertIn("--no-browser", cmd)
        self.assertIn("--port=9001", cmd)


if __name__ == "__main__":
    unittest.main()
