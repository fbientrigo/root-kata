from __future__ import annotations
import importlib.util, json, os, subprocess, sys, tempfile
from pathlib import Path
from typing import Any
from .catalog import get_exercise, repository_root


def missing_requirements(requirements: list[str]) -> list[str]: return [name for name in requirements if importlib.util.find_spec(name) is None]


def grade_code(exercise_id: str, code: str, *, timeout_seconds: float = 8.0) -> dict[str, Any]:
    metadata, exercise_dir = get_exercise(exercise_id)
    if metadata.get("kind") == "cpp":
        from .cpp_runner import run_cpp, work_dir
        with tempfile.TemporaryDirectory(prefix="root-kata-") as tmp:
            src = Path(tmp) / metadata["starter"]; src.write_text(code, encoding="utf-8")
            return run_cpp(exercise_id, src, timeout_seconds=max(timeout_seconds, 10.0), work=work_dir(exercise_id, Path(tempfile.gettempdir()) / "root-kata-web"))
    missing = missing_requirements(metadata.get("requires", []))
    if missing:
        names = ", ".join(missing)
        return {"status": "runtime_missing", "passed": False, "summary": f"Missing runtime requirement: {names}",
                "_sid": "sum.missing_req", "_params": {"names": names}, "cases": [], "stdout": "", "stderr": ""}
    with tempfile.TemporaryDirectory(prefix="root-kata-") as tmp:
        solution_path = Path(tmp)/"solution.py"; solution_path.write_text(code,encoding="utf-8"); env=os.environ.copy(); src_dir=repository_root()/"src"; current=env.get("PYTHONPATH",""); env["PYTHONPATH"]=str(src_dir)+(os.pathsep+current if current else "")
        cmd=[sys.executable,"-m","root_kata.grader_worker",str(exercise_dir),str(solution_path),metadata["validator"]]
        try: proc=subprocess.run(cmd,capture_output=True,text=True,timeout=timeout_seconds,env=env,cwd=str(exercise_dir))
        except subprocess.TimeoutExpired:
            return {"status": "timeout", "passed": False, "summary": f"Execution exceeded {timeout_seconds:g} seconds",
                    "_sid": "sum.exec_timeout", "_params": {"seconds": f"{timeout_seconds:g}"}, "cases": [], "stdout": "", "stderr": ""}
        if proc.returncode != 0:
            return {"status": "grader_error", "passed": False, "summary": "The grading worker failed",
                    "_sid": "sum.grader_failed", "cases": [], "stdout": "", "stderr": proc.stderr[-4000:]}
        try:
            return json.loads(proc.stdout)
        except json.JSONDecodeError:
            return {"status": "grader_error", "passed": False, "summary": "The grading worker returned invalid output",
                    "_sid": "sum.grader_bad_output", "cases": [], "stdout": proc.stdout[-4000:], "stderr": proc.stderr[-4000:]}
