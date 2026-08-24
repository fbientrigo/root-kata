"""Compile-and-run pipeline for `kind: "cpp"` exercises.

Design goals (in priority order):
1. Every failure has exactly ONE classification and ONE first thing to look at.
2. Everything the runner did is reproducible by hand: the exact compile command,
   the full compiler log and the binary all live in a persistent work directory.
3. No Cling, no PyROOT. Student code is compiled with the real compiler using
   `root-config`, so error messages are the ones the student will see in real life.

Pipeline:
    solution.cpp (student)  +  harness.cpp (teacher)  --g++-->  harness binary
    binary --stdout--> JSON {case_name: value, ...}
    validator.grade(results) --> [Case...]   (pure Python, ROOT not needed here)

Status values produced:
    runtime_missing   g++ / root-config not found
    compile_error     compiler returned non-zero
    runtime_error     binary crashed / non-zero exit / timeout
    harness_error     binary ran but did not print valid JSON (teacher bug, usually)
    passed / failed   validator ran
"""
from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from .catalog import get_exercise

_ERR_RE = re.compile(r"^(?P<file>[^:\n]+):(?P<line>\d+):(?:(?P<col>\d+):)?\s*(?:fatal )?error:\s*(?P<msg>.*)$", re.M)


def work_dir(exercise_id: str, base: Path | None = None) -> Path:
    base = base or Path(os.environ.get("ROOT_KATA_WORK", ".root-kata")).expanduser()
    d = (base / exercise_id).resolve()
    d.mkdir(parents=True, exist_ok=True)
    return d


def _which_compiler() -> str | None:
    for name in (os.environ.get("CXX"), "g++", "clang++", "c++"):
        if name and shutil.which(name):
            return name
    return None


def root_config_flags() -> tuple[list[str], list[str]] | None:
    """Return (cflags, libs) from root-config, or None if ROOT is not on PATH."""
    if not shutil.which("root-config"):
        return None
    try:
        cflags = subprocess.run(["root-config", "--cflags"], capture_output=True, text=True, check=True).stdout.split()
        libs = subprocess.run(["root-config", "--libs"], capture_output=True, text=True, check=True).stdout.split()
    except (subprocess.CalledProcessError, OSError):
        return None
    return cflags, libs


def _result(status: str, summary: str, **extra: Any) -> dict[str, Any]:
    base = {"status": status, "passed": status == "passed", "summary": summary, "cases": [],
            "stdout": "", "stderr": "", "first_error": None, "work_dir": None}
    base.update(extra)
    return base


def _first_error(log: str, student_file: Path) -> dict[str, Any] | None:
    """Pick the first `error:` line, preferring ones in the student's file, and attach code context."""
    matches = list(_ERR_RE.finditer(log))
    if not matches:
        return None
    student_hits = [m for m in matches if Path(m.group("file")).name == student_file.name]
    m = (student_hits or matches)[0]
    line = int(m.group("line"))
    context = []
    try:
        src = Path(m.group("file")).read_text(encoding="utf-8", errors="replace").splitlines()
        for n in range(max(1, line - 2), min(len(src), line + 2) + 1):
            context.append(f"{'>' if n == line else ' '} {n:4d} | {src[n - 1]}")
    except OSError:
        pass
    return {"file": Path(m.group("file")).name, "line": line, "message": m.group("msg").strip(),
            "context": "\n".join(context), "in_student_file": bool(student_hits)}


def _signal_name(code: int) -> str:
    try:
        return signal.Signals(-code).name
    except (ValueError, AttributeError):
        return f"exit {code}"


def run_cpp(exercise_id: str, solution_path: Path, *, timeout_seconds: float = 10.0,
            work: Path | None = None) -> dict[str, Any]:
    metadata, exercise_dir = get_exercise(exercise_id)
    wd = work or work_dir(exercise_id)
    wd.mkdir(parents=True, exist_ok=True)
    solution_path = Path(solution_path).resolve()

    cxx = _which_compiler()
    if cxx is None:
        return _result("runtime_missing", "No C++ compiler found (tried $CXX, g++, clang++). Install one and re-run doctor().", work_dir=str(wd))

    needs_root = "ROOT" in metadata.get("requires", [])
    cflags: list[str] = ["-std=c++17"]
    libs: list[str] = []
    if needs_root:
        flags = root_config_flags()
        if flags is None:
            return _result("runtime_missing", "root-config not found on PATH. Source ROOT (e.g. `source /path/to/root/bin/thisroot.sh`) before starting Jupyter.", work_dir=str(wd))
        cflags, libs = flags

    harness = exercise_dir / metadata["harness"]
    include_dir = Path(__file__).resolve().parent / "include"
    binary = wd / "harness"
    shutil.copy2(harness, wd / harness.name)
    shutil.copy2(solution_path, wd / metadata["starter"])
    cmd = [cxx, *cflags, f"-I{include_dir}", f"-I{exercise_dir}", "-o", str(binary), str(wd / harness.name), *libs]
    (wd / "compile.sh").write_text("#!/bin/sh\n# Exact command ROOT Kata used. Run it yourself to reproduce.\n" + shlex.join(cmd) + "\n")

    t0 = time.perf_counter()
    try:
        build = subprocess.run(cmd, capture_output=True, text=True, cwd=str(wd), timeout=120)
    except subprocess.TimeoutExpired:
        return _result("compile_error", "Compiler did not finish within 120 s", work_dir=str(wd))
    build_ms = round((time.perf_counter() - t0) * 1000)
    (wd / "build.log").write_text("$ " + shlex.join(cmd) + "\n\n" + build.stdout + build.stderr)

    if build.returncode != 0:
        err = _first_error(build.stderr, solution_path)
        summary = "Compilation failed"
        if err:
            where = f"{err['file']}:{err['line']}"
            summary = f"Compilation failed at {where}: {err['message']}"
        return _result("compile_error", summary, first_error=err, stderr=build.stderr[-4000:],
                       work_dir=str(wd), build_ms=build_ms)

    t0 = time.perf_counter()
    try:
        run = subprocess.run([str(binary)], capture_output=True, text=True, cwd=str(wd), timeout=timeout_seconds)
    except subprocess.TimeoutExpired as exc:
        (wd / "run.log").write_text((exc.stdout or "") if isinstance(exc.stdout, str) else "")
        return _result("runtime_error", f"Your program ran longer than {timeout_seconds:g} s (infinite loop?)",
                       work_dir=str(wd), build_ms=build_ms)
    run_ms = round((time.perf_counter() - t0) * 1000)
    (wd / "run.log").write_text("$ ./harness\n\n--- stdout ---\n" + run.stdout + "\n--- stderr ---\n" + run.stderr)

    if run.returncode != 0:
        reason = _signal_name(run.returncode) if run.returncode < 0 else f"exit code {run.returncode}"
        hint = " (segfault: probably an out-of-range index, a null pointer, or an uninitialised histogram)" if reason == "SIGSEGV" else ""
        return _result("runtime_error", f"Your program crashed: {reason}{hint}", stderr=run.stderr[-4000:],
                       stdout=run.stdout[-4000:], work_dir=str(wd), build_ms=build_ms, run_ms=run_ms)

    lines = run.stdout.rstrip("\n").splitlines()
    try:
        results = json.loads(lines[-1]) if lines else None
        if not isinstance(results, dict):
            raise ValueError
    except (ValueError, json.JSONDecodeError):
        return _result("harness_error", "The harness did not produce JSON on its last stdout line. Check run.log (did you print something after rk::done()?).",
                       stdout=run.stdout[-4000:], stderr=run.stderr[-4000:], work_dir=str(wd))
    student_stdout = "\n".join(lines[:-1])

    validator_path = exercise_dir / metadata["validator"]
    import importlib.util
    spec = importlib.util.spec_from_file_location(f"root_kata_validator_{exercise_id}", validator_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    cases = [c.run() for c in mod.grade(results)]
    n_pass = sum(c["passed"] for c in cases)
    status = "passed" if cases and n_pass == len(cases) else "failed"
    return _result(status, f"{n_pass}/{len(cases)} tests passed", cases=cases, stdout=student_stdout[-4000:],
                   stderr=run.stderr[-4000:], work_dir=str(wd), build_ms=build_ms, run_ms=run_ms)
