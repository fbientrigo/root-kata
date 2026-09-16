#!/usr/bin/env python3
"""Run every shipped ROOT Kata in native ROOT and in wasm ROOT in the browser,
and require the two to agree and to pass the kata's own validator.

This is the first check that exercises the *curriculum* rather than a probe
program written for the experiment: the harness, the rk.h emitter and the
validator are the repository's own, read and never modified (wasm/GATES.md:52).

Per exercise:
  native arm   compile harness.cpp + the reference solution with the pinned
               native ROOT and run it; the rk JSON is the last stdout line.
  browser arm  build the same translation unit with rk.h and the solution
               inlined -- the browser kernel compiles one cell and has no
               include path for them -- and run it through
               wasm/gates/rootweb/run.sh cell.
  assert       the two rk JSON objects are identical, and the exercise's own
               validator.grade() passes on the browser's JSON.

Two exercises are expected to be BLOCKED and are asserted as such, so they
cannot pass by accident and cannot be forgotten. Both stop at the same place,
TInterpreter::SetClassInfo:
  cpp-root-fit-gaussian a correct solution calls TH1::Fit, which needs TClass
                        reflection to resolve its minimizer.
  cpp-root-histogram    its harness draws into a TCanvas, but reflection is
                        reached before any graphics symbol is.

Usage: sweep.py [exercise-id ...]   (default: every exercise with a solution)
"""
import json
import importlib.util
import os
import pathlib
import subprocess
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[3]
HERE = REPO / "wasm/gates/rootkatas"
SOLUTIONS = HERE / "solutions"
EXERCISES = REPO / "src/root_kata/exercises"
RK_H = REPO / "src/root_kata/include/rk.h"
ROOTWEB = REPO / "wasm/gates/rootweb/run.sh"
WEB_BUILD = REPO / "wasm/build/rootweb"
HOST_ROOT = pathlib.Path.home() / ".cache/rootwasm-p0/xbuild/root-6.40.04-host/root"
OUT = pathlib.Path.home() / ".cache/rootwasm-p0/rootkatas"

# Exercise -> the milestone that unblocks it. These must fail, and must say why.
#
# Measured, not assumed: both stop at the *same* place, TInterpreter::SetClassInfo.
# cpp-root-histogram was expected to fail on its TCanvas, but TClass reflection is
# reached first, so M4b is what unblocks both. Whether the canvas then needs M5
# graphics is unknown until reflection lands.
_REFLECTION = ("SetClassInfo", "not implemented in wasm ROOT")
BLOCKED = {
    "cpp-root-histogram": ("M4b TClass reflection (its TCanvas may then need M5)",
                           _REFLECTION),
    "cpp-root-fit-gaussian": ("M4b TClass reflection", _REFLECTION),
}


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def last_json_line(stdout):
    """rk::done() prints the results as the last line of stdout."""
    lines = [ln for ln in (stdout or "").splitlines() if ln.strip()]
    if not lines:
        return None, "no output", None
    try:
        value = json.loads(lines[-1])
    except json.JSONDecodeError as exc:
        return None, f"last stdout line is not JSON ({exc}): {lines[-1][:120]!r}", None
    if not isinstance(value, dict):
        return None, f"last stdout line is not a JSON object: {lines[-1][:120]!r}", None
    return value, None, lines[-1]


def native_json(eid, solution, workdir):
    """Compile and run the exercise's own harness against the pinned native ROOT."""
    exdir = EXERCISES / eid
    (workdir / "solution.cpp").write_text(solution)
    meta = json.loads((exdir / "exercise.json").read_text())
    harness = exdir / meta["harness"]
    (workdir / harness.name).write_text(harness.read_text())

    cflags = ["-std=c++17"]
    libs = []
    if "ROOT" in meta.get("requires", []):
        rc = run([str(HOST_ROOT / "bin/root-config"), "--cflags"], env={"PATH": "/usr/bin:/bin"})
        cflags = rc.stdout.split()
        libs = ["-L" + str(HOST_ROOT / "lib"), "-Wl,-rpath," + str(HOST_ROOT / "lib"),
                "-lHist", "-lCore", "-lMathCore", "-lGraf", "-lGpad", "-lRIO"]
    cmd = ["g++", *cflags, f"-I{RK_H.parent}", f"-I{exdir}", "-o", str(workdir / "harness"),
           str(workdir / harness.name), *libs]
    r = run(cmd, cwd=workdir)
    if r.returncode != 0:
        return None, "native compile failed: " + (r.stderr.strip().splitlines() or ["?"])[-1][:200], None
    r = run([str(workdir / "harness")], cwd=workdir)
    if r.returncode != 0:
        return None, f"native run failed (exit {r.returncode}): {r.stderr.strip()[-200:]}", None
    return last_json_line(r.stdout)


def browser_cell(eid, solution):
    """One translation unit: the unmodified harness with its two local includes inlined."""
    meta = json.loads((EXERCISES / eid / "exercise.json").read_text())
    text = (EXERCISES / eid / meta["harness"]).read_text()
    text = text.replace('#include "rk.h"', RK_H.read_text(), 1)
    text = text.replace('#include "solution.cpp"', solution, 1)
    return text


def browser_json(eid, solution, workdir):
    cell = workdir / f"{eid}.cxx"
    cell.write_text(browser_cell(eid, solution))
    # Stage the 124 MB web root once for the whole sweep, then only swap the
    # cell: 13 re-stagings are slow, and they also re-read the shared $ROOTSYS
    # that another gate may be rebuilding at the same time.
    env = dict(os.environ, ROOTWEB_REUSE="1")
    r = run(["bash", str(ROOTWEB), "cell", str(cell)], env=env)
    if r.returncode != 0:
        return None, "browser run failed: " + (r.stdout + r.stderr).strip()[-300:], "", None
    stdout = (WEB_BUILD / "cell_stdout.txt").read_text()
    diag = (WEB_BUILD / "cell_diag.txt").read_text()
    value, err, raw = last_json_line(stdout)
    return value, err, diag, raw


def grade(eid, results):
    """Run the exercise's own validator on an rk JSON dict."""
    sys.path.insert(0, str(REPO / "src"))
    path = EXERCISES / eid / "validator.py"
    spec = importlib.util.spec_from_file_location(f"rootkatas_validator_{eid}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return [c.run() for c in mod.grade(results)]


def check(eid):
    """Returns (ok, one-line summary, detail lines)."""
    solution = (SOLUTIONS / f"{eid}.cpp").read_text()
    detail = []
    with tempfile.TemporaryDirectory(prefix=f"rootkatas-{eid}-") as tmp:
        work = pathlib.Path(tmp)
        bjson, berr, bdiag, braw = browser_json(eid, solution, work)

        if eid in BLOCKED:
            milestone, needles = BLOCKED[eid]
            njson, nerr, _ = native_json(eid, solution, work)
            if njson is None:
                return False, f"blocked fixture failed natively: {nerr}", []
            native_failed = [c for c in grade(eid, njson) if not c["passed"]]
            if native_failed:
                detail += [f"    - {c['name']}: {c['message']}" for c in native_failed]
                return False, "blocked fixture is not a valid native solution", detail
            haystack = (bdiag or "") + json.dumps(bjson or {})
            if bjson is not None and all(c["passed"] for c in grade(eid, bjson)):
                return False, f"unexpectedly PASSED, but {milestone} is not implemented", []
            if not any(n in haystack for n in needles):
                detail.append("    diag: " + (bdiag or berr or "").strip()[:300])
                return False, f"blocked, but did not say why (expected one of {needles})", detail
            return True, f"valid natively; BLOCKED as expected, awaiting {milestone}", []

        if bjson is None:
            detail.append("    diag: " + (bdiag or "").strip()[:400])
            return False, f"browser produced no rk JSON: {berr}", detail

        njson, nerr, nraw = native_json(eid, solution, work)
        if njson is None:
            return False, f"native arm failed: {nerr}", []

        if njson != bjson:
            for key in sorted(set(njson) | set(bjson)):
                if njson.get(key) != bjson.get(key):
                    detail.append(f"    {key}: native={njson.get(key)!r} browser={bjson.get(key)!r}")
            return False, "browser rk JSON differs from native ROOT", detail

        if nraw != braw:
            detail += [f"    native={nraw!r}", f"    browser={braw!r}"]
            return False, "browser rk JSON is not byte-identical to native ROOT", detail

        cases = grade(eid, bjson)
        failed = [c for c in cases if not c["passed"]]
        if failed:
            detail += [f"    - {c['name']}: {c['message']}" for c in failed]
            return False, f"validator rejected the browser result ({len(failed)} case(s))", detail
        return True, f"identical to native, validator passed {len(cases)}/{len(cases)}", []


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    wanted = sys.argv[1:] or sorted(p.stem for p in SOLUTIONS.glob("*.cpp"))
    failures = []
    for eid in wanted:
        ok, summary, detail = check(eid)
        print(f"    {eid:38s} {'ok ' if ok else 'FAIL'} {summary}", flush=True)
        for line in detail:
            print(line, flush=True)
        if not ok:
            failures.append(eid)
    print(f"\n    {len(wanted) - len(failures)}/{len(wanted)} exercise checks passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
