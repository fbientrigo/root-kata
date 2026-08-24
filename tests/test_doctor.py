import importlib
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

# `root_kata.doctor` is shadowed by a public function of the same name in
# root_kata/__init__.py; go through sys.modules to reach the module itself.
importlib.import_module("root_kata.doctor")
doctor_mod = sys.modules["root_kata.doctor"]

ENV_PY = "/opt/conda/envs/root-kata/bin"
FOREIGN_PY = "/home/student/.local/bin"


class EntryPointMismatchTests(unittest.TestCase):
    def test_detects_root_kata_installed_in_another_environment(self):
        with mock.patch.object(doctor_mod.shutil, "which", return_value=f"{FOREIGN_PY}/root-kata"), \
                mock.patch.object(doctor_mod.sys, "executable", f"{ENV_PY}/python"):
            msg = doctor_mod._entry_point_mismatch()
        self.assertIsNotNone(msg)
        self.assertIn(FOREIGN_PY, msg)

    def test_accepts_entry_point_from_same_environment(self):
        with mock.patch.object(doctor_mod.shutil, "which", return_value=f"{ENV_PY}/root-kata"), \
                mock.patch.object(doctor_mod.sys, "executable", f"{ENV_PY}/python"):
            self.assertIsNone(doctor_mod._entry_point_mismatch())

    def test_reports_missing_entry_point(self):
        with mock.patch.object(doctor_mod.shutil, "which", return_value=None), \
                mock.patch.object(doctor_mod.sys, "executable", f"{ENV_PY}/python"):
            self.assertIsNotNone(doctor_mod._entry_point_mismatch())


if __name__ == "__main__":
    unittest.main()
