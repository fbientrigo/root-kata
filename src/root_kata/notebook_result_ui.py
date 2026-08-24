from __future__ import annotations

import html
from typing import Any

from .notebook_ui import progress_html


def format_html(r: dict[str, Any], meta: dict[str, Any]) -> str:
    status = r.get("status", "")
    accent, label = {"passed": ("#1a7f37", "Solved"), "failed": ("#b35900", "Not yet"), "compile_error": ("#b42318", "Compile error"), "runtime_error": ("#b42318", "Runtime error"), "solution_error": ("#b42318", "Code error"), "timeout": ("#b42318", "Timeout")}.get(status, ("#57606a", "Check result"))
    summary = html.escape(str(r.get("summary", "")))
    next_action = {"passed": "All visible tests pass. Your solution has been saved locally.", "failed": "Start with the first failing case: compare what it expected with what your code produced.", "compile_error": "Fix the first compiler error shown below, then run this cell again.", "runtime_error": "Use the runtime message below to identify where execution stopped.", "solution_error": "Fix the first error in your code, then run this cell again.", "timeout": "Check for a loop or operation that never terminates."}.get(status, "Inspect the details below, then run the cell again.")
    timing = ""
    if r.get("build_ms") is not None:
        bits = [f"compile {r['build_ms']} ms"]
        if r.get("run_ms") is not None: bits.append(f"run {r['run_ms']} ms")
        timing = f'<span style="opacity:.6;font-size:.85rem;">{" · ".join(bits)}</span>'
    first_error = ""; fe = r.get("first_error")
    if fe:
        context = html.escape(str(fe.get("context") or "")); note = ""
        if not fe.get("in_student_file"): note = '<div style="margin-top:.45rem;font-size:.9rem;">The harness reported this. Check that your function signature exactly matches the problem statement.</div>'
        first_error = '<pre style="overflow:auto;margin:.65rem 0 0;padding:.75rem;border-radius:8px;background:rgba(127,127,127,.09);white-space:pre-wrap;">' + context + '</pre>' + note
    cases = []
    for case in r.get("cases", []):
        passed = bool(case.get("passed")); detail = ""
        if not passed:
            detail = f'<div style="margin:.18rem 0 0 1.55rem;opacity:.82;font-size:.9rem;">{html.escape(str(case.get("message", "")))}'
            if case.get("expected") is not None:
                detail += f' <span style="white-space:nowrap;">Expected <code>{html.escape(str(case.get("expected")))}</code>; got <code>{html.escape(str(case.get("actual")))}</code>.</span>'
            detail += '</div>'
        cases.append('<li style="list-style:none;padding:.42rem 0;border-top:1px solid rgba(127,127,127,.12);">' + f'<span aria-hidden="true" style="display:inline-block;width:1.55rem;font-weight:700;">{"✓" if passed else "✕"}</span><span>{html.escape(str(case.get("name", "test")))}</span>{detail}</li>')
    case_block = ""; test_progress = ""
    if cases:
        raw = r.get("cases", []); test_progress = progress_html(sum(bool(c.get("passed")) for c in raw), len(raw), label="Tests", accent=accent); case_block = '<ul aria-label="Visible test results" style="padding:0;margin:.65rem 0 0;">' + ''.join(cases) + '</ul>'
    extra = []
    if status in ("runtime_error", "solution_error", "harness_error") and r.get("stderr"):
        stderr = html.escape("\n".join(str(r["stderr"]).strip().splitlines()[-8:])); extra.append(f'<details><summary>stderr</summary><pre style="white-space:pre-wrap;overflow:auto;">{stderr}</pre></details>')
    if r.get("stdout"):
        stdout = html.escape("\n".join(str(r["stdout"]).strip().splitlines()[-8:])); extra.append(f'<details><summary>Your output</summary><pre style="white-space:pre-wrap;overflow:auto;">{stdout}</pre></details>')
    if r.get("work_dir"):
        work = html.escape(str(r["work_dir"])); extra.append(f'<details><summary>Reproduce outside Jupyter</summary><code>sh {work}/compile.sh</code><div style="margin-top:.35rem;opacity:.75;">Logs: {work}/build.log · {work}/run.log</div></details>')
    hints = meta.get("hints", [])
    if status != "passed" and hints: extra.append(f'<details><summary>Need a hint?</summary><div style="margin-top:.45rem;">{html.escape(str(hints[0]))}</div></details>')
    extras = ''.join(f'<div style="margin-top:.55rem;">{x}</div>' for x in extra)
    badges = ''.join(f'<span style="display:inline-block;margin:.35rem .35rem 0 0;padding:.2rem .48rem;border:1px solid rgba(127,127,127,.25);border-radius:999px;">🏅 {html.escape(str(b))}</span>' for b in r.get("new_badges", []))
    return f'''<section role="status" aria-live="polite" style="max-width:860px;border:1px solid rgba(127,127,127,.25);border-left:5px solid {accent};border-radius:12px;padding:1rem 1.15rem;margin:.35rem 0 1rem;line-height:1.45;"><header style="display:flex;justify-content:space-between;align-items:baseline;gap:1rem;flex-wrap:wrap;"><div><span style="font-size:.78rem;text-transform:uppercase;letter-spacing:.055em;font-weight:700;">{label}</span><h3 style="font-size:1.1rem;margin:.2rem 0;">{summary}</h3></div>{timing}</header><div style="margin:.5rem 0 .2rem;">{html.escape(next_action)}</div>{first_error}{test_progress}{case_block}{extras}{badges}</section>'''
