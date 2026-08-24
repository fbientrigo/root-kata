"""Notebook-first API for ROOT Kata."""
from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any

from . import i18n
from . import progress as _progress
from .catalog import get_exercise, localized
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
                print(i18n.t("magic_usage"))
                return
            check(exercise_id, cell)
        ipython.register_magic_function(kata, "cell", "kata")
    if announce:
        print(i18n.t("magic_loaded"))


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
    view = localized(meta)
    if _in_notebook():
        _display(_statement_text(view, exercise_id), _statement_html(view, exercise_id, cell_ready=cell_ready))
    else:
        print(i18n.t("keeping_existing", path=dst) if existed else i18n.t("created_path", path=dst))
        print(_statement_text(view, exercise_id))


def show(exercise_id: str) -> None:
    view = localized(get_exercise(exercise_id)[0])
    _display(_statement_text(view, exercise_id), _statement_html(view, exercise_id, cell_ready=None))


def tests(exercise_id: str) -> None:
    meta, ex_dir = get_exercise(exercise_id)
    name = meta["harness"] if meta["kind"] == "cpp" else meta["validator"]
    print(f"--- {name} ---")
    print((ex_dir / name).read_text(encoding="utf-8"))
    if meta["kind"] == "cpp":
        print("---", meta["validator"], "---")
        print((ex_dir / meta["validator"]).read_text(encoding="utf-8"))


def hint(exercise_id: str, n: int = 1) -> None:
    meta = localized(get_exercise(exercise_id)[0])
    hints = meta.get("hints", [])
    if not hints:
        print(i18n.t("no_hints"))
        return
    for i, h in enumerate(hints[:n], 1):
        print(i18n.t("hint_n", i=i, n=len(hints), hint=h))


def check(exercise_id: str, code: str | None = None, *, timeout: float = 10.0) -> dict[str, Any]:
    meta, _ = get_exercise(exercise_id)
    path = solution_path(exercise_id)
    if code is not None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(code, encoding="utf-8")
    if not path.exists():
        print(i18n.t("no_solution_yet", exercise_id=exercise_id, path=path))
        return {"status": "not_started", "passed": False}
    if meta["kind"] == "cpp":
        result = run_cpp(exercise_id, path, timeout_seconds=timeout)
    else:
        result = grade_code(exercise_id, path.read_text(encoding="utf-8"), timeout_seconds=timeout)
    view = localized(meta)
    result["exercise_id"] = exercise_id
    result["new_badges"] = _progress.record(exercise_id, result)
    result["_meta"] = view
    _display(_format_text(result), _format_html(result, view))
    return result


def doctor() -> bool:
    return _doctor(KATA_DIR, in_notebook=_in_notebook())


def progress() -> dict[str, Any]:
    from .catalog import badge_label, difficulty_label
    s = _progress.summary()
    out = [i18n.t("progress_solved", n=s["n_solved"], m=s["n_total"]), ""]
    for e in s["exercises"]:
        view = localized(e)
        mark = "✅" if e["solved"] else ("🔁" if e["attempts"] else "⬜")
        suffix = "   " + i18n.t("attempts_count", n=e["attempts"]) if e["attempts"] else ""
        out.append(f"  {mark} {e['id']:<24} {difficulty_label(view['difficulty']):<8} {view['title']}" + suffix)
    out.append("")
    badges = ", ".join(f"🏅 {badge_label(b)}" for b in sorted(s["badges"])) if s["badges"] else i18n.t("badges_none")
    out.append(i18n.t("badges_prefix") + " " + badges)
    print("\n".join(out))
    return s


export = _progress.export


def load_ipython_extension(ipython) -> None:  # noqa: ANN001
    _register_kata_magic(ipython, announce=True)
