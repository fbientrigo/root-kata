from __future__ import annotations
import contextlib,importlib.util,io,json,sys,traceback
from pathlib import Path

def _best_effort_limits()->None:
    try:
        import resource
        resource.setrlimit(resource.RLIMIT_CPU,(6,7))
    except Exception:pass
def _load_module(name:str,path:Path):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None:raise ImportError(f"Cannot import {path}")
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
def main()->int:
    _best_effort_limits()
    if len(sys.argv)!=4:return 2
    exercise_dir=Path(sys.argv[1]);solution_path=Path(sys.argv[2]);validator_path=exercise_dir/sys.argv[3];captured_out=io.StringIO();captured_err=io.StringIO()
    try:
        with contextlib.redirect_stdout(captured_out),contextlib.redirect_stderr(captured_err):
            solution=_load_module("root_kata_student_solution",solution_path);validator=_load_module("root_kata_exercise_validator",validator_path);raw_cases=validator.grade(solution);cases=[item.run() if hasattr(item,"run") else item for item in raw_cases]
        passed=bool(cases) and all(item.get("passed") for item in cases);result={"status":"passed" if passed else "failed","passed":passed,"summary":f"{sum(bool(c.get('passed')) for c in cases)}/{len(cases)} cases passed","cases":cases,"stdout":captured_out.getvalue()[-4000:],"stderr":captured_err.getvalue()[-4000:]}
    except Exception as exc:result={"status":"solution_error","passed":False,"summary":f"{type(exc).__name__}: {exc}","cases":[],"stdout":captured_out.getvalue()[-4000:],"stderr":(captured_err.getvalue()+traceback.format_exc())[-4000:]}
    sys.stdout.write(json.dumps(result));return 0
if __name__=="__main__":raise SystemExit(main())
