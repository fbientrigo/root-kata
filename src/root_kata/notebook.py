"""Notebook-first API for ROOT Kata."""
from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any

from . import progress as _progress
from .catalog import get_exercise
from .cpp_runner import run_cpp
from .doctor import doctor as _doctor
from .grader import grade_code
from .notebook_result_ui import format_html as _format_html
from .notebook_ui import format_text as _format_text
from .notebook_ui import progress_html as _progress_html
from .notebook_ui import statement_html as _statement_html_impl
from .notebook_ui import statement_text as _statement_text_impl

KATA_DIR = Path(os.environ.get("ROOT_KATA_DIR", "kata"))


def _in_notebook() -> bool:
    try:
        from IPython import get_ipython  # type: ignore
        ip = get_ipython()
        return ip is not None and "IPKernelApp" in ip.config
    except Exception:
        return False


def _display(text: str, html_block: str | None = None) -> None:
    if html_block and _in_notebook():
        from IPython.display import HTML, display  # type: ignore
        display(HTML(html_block))
    else:
        print(text)


def _starter_cell(exercise_id: str, code: str) -> str:
    return f"%%kata {exercise_id}\n{code.rstrip()}\n"


def _register_kata_magic(ipython, *, announce: bool) -> None:  # noqa: ANN001
    magics = getattr(getattr(ipython, "magics_manager", None), "magics", {})
    if "kata" not in magics.get("cell", {}):
        def kata(line: str, cell: str) -> None:
            exercise_id = line.strip().split()[0] if line.strip() else ""
            if not exercise_id:
                print("usage: %%kata <exercise-id>")
                return
            check(exercise_id, cell)
        ipython.register_magic_function(kata, "cell", "kata")
    if announce:
        print("root_kata loaded: use %%kata <exercise-id> at the top of a cell.")


def _prepare_notebook_cell(exercise_id: str, code: str) -> bool:
    if not _in_notebook():
        return False
    try:
        from IPython import get_ipython  # type: ignore
        ip = get_ipython()
        if ip is None or not hasattr(ip, "set_next_input"):
            return False
        _register_kata_magic(ip, announce=False)
        ip.set_next_input(_starter_cell(exercise_id, code), replace=False)
        return True
    except Exception:
        return False


def solution_path(exercise_id: str) -> Path:
    meta, _ = get_exercise(exercise_id)
    return KATA_DIR / exercise_id / meta["starter"]


def _statement_text(meta: dict[str, Any], exercise_id: str) -> str:
    return _statement_text_impl(meta, exercise_id, solution_path(exercise_id))


def _statement_html(meta: dict[str, Any], exercise_id: str, *, cell_ready: bool | None) -> str:
    return _statement_html_impl(meta, exercise_id, solution_path(exercise_id), cell_ready=cell_ready)


def start(exercise_id: str, *, force: bool = False) -> None:
    meta, ex_dir = get_exercise(exercise_id)
    dst = solution_path(exercise_id)
    dst.parent.mkdir(parents=True, exist_ok=True)
    existed = dst.exists() and not force
    if not existed:
        shutil.copy2(ex_dir / meta["starter"], dst)
    code = dst.read_text(encoding="utf-8")
    cell_ready = _prepare_notebook_cell(exercise_id, code)
    if _in_notebook():
        _display(_statement_text(meta, exercise_id), _statement_html(meta, exercise_id, cell_ready=cell_ready))
    else:
        print(f"(keeping your existing {dst})" if existed else f"Created {dst}")
        print(_statement_text(meta, exercise_id))


def show(exercise_id: str) -> None:
    meta, _ = get_exercise(exercise_id)
    _display(_statement_text(meta, exercise_id), _statement_html(meta, exercise_id, cell_ready=None))


def tests(exercise_id: str) -> None:
    meta, ex_dir = get_exercise(exercise_id)
    name = meta["harness"] if meta["kind"] == "cpp" else meta["validator"]
    print(f"--- {name} ---")
    print((ex_dir / name).read_text(encoding="utf-8"))
    if meta["kind"] == "cpp":
        print(f"--- {meta['validator']} (what each value must satisfy) ---")
        print((ex_dir / meta["validator"]).read_text(encoding="utf-8"))


def hint(exercise_id: str, n: int = 1) -> None:
    hints = get_exercise(exercise_id)[0].get("hints", [])
    if not hints:
        print("No hints for this exercise.")
        return
    for i, h in enumerate(hints[:n], 1):
        print(f"hint {i}/{len(hints)}: {h}")


def check(exercise_id: str, code: str | None = None, *, timeout: float = 10.0) -> dict[str, Any]:
    meta, _ = get_exercise(exercise_id)
    path = solution_path(exercise_id)
    if code is not None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(code, encoding="utf-8")
    if not path.exists():
        print(f"No solution yet. Run rk.start('{exercise_id}') first (it creates {path}).")
        return {"status": "not_started", "passed": False}
    if meta["kind"] == "cpp":
        result = run_cpp(exercise_id, path, timeout_seconds=timeout)
    else:
        result = grade_code(exercise_id, path.read_text(encoding="utf-8"), timeout_seconds=timeout)
    result["_badge"] = meta.get("badge")
    result["exercise_id"] = exercise_id
    result["new_badges"] = _progress.record(exercise_id, result)
    _display(_format_text(result), _format_html(result, meta))
    return result


def doctor() -> bool:
    return _doctor(KATA_DIR, in_notebook=_in_notebook())


def progress() -> dict[str, Any]:
    s = _progress.summary()
    out = [f"Solved {s['n_solved']}/{s['n_total']}", ""]
    for e in s["exercises"]:
        mark = "✅" if e["solved"] else ("🔁" if e["attempts"] else "⬜")
        out.append(f"  {mark} {e['id']:<24} {e['difficulty']:<6} {e['title']}" + (f"   ({e['attempts']} attempts)" if e["attempts"] else ""))
    out.append("")
    out.append("Badges: " + (", ".join(f"🏅 {b}" for b in s["badges"]) if s["badges"] else "none yet"))
    print("\n".join(out))
    return s


export = _progress.export


def load_ipython_extension(ipython) -> None:  # noqa: ANN001
    _register_kata_magic(ipython, announce=True)
