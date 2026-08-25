from __future__ import annotations

import base64
import html
from pathlib import Path
from typing import Any

from . import i18n
from .catalog import case_label, message_label
from .notebook_ui import _summary, progress_html

PAGES_URL = "https://fbientrigo.github.io/root-kata/"


def format_html(r: dict[str, Any], meta: dict[str, Any]) -> str:
    status = r.get("status", "")
    accent_key = "passed" if status == "passed" else status
    accent, label = {
        "passed": ("#1a7f37", i18n.t("status.passed")),
        "failed": ("#b35900", i18n.t("status.failed")),
        "compile_error": ("#b42318", i18n.t("status.compile_error")),
        "runtime_error": ("#b42318", i18n.t("status.runtime_error")),
        "solution_error": ("#b42318", i18n.t("status.solution_error")),
        "timeout": ("#b42318", i18n.t("status.timeout")),
    }.get(accent_key, ("#57606a", i18n.t("status.check_result")))
    summary = html.escape(_summary(r))
    next_action = {"passed": "next.passed", "failed": "next.failed", "compile_error": "next.compile_error",
                   "runtime_error": "next.runtime_error", "solution_error": "next.solution_error",
                   "timeout": "next.timeout"}.get(status)
    next_text = html.escape(i18n.t(next_action) if next_action else i18n.t("next.default"))
    preview_block = ""
    preview = r.get("preview")
    if preview and preview.get("path"):
        try:
            data = base64.b64encode(Path(preview["path"]).read_bytes()).decode("ascii")
        except OSError:
            data = None
        if data:
            alt = html.escape(str((meta.get("preview") or {}).get("alt") or i18n.t("preview_alt_default")))
            preview_block = (f'<div style="margin:.7rem 0;"><img src="data:image/png;base64,{data}" alt="{alt}" '
                             f'style="max-width:100%;display:block;border-radius:10px;border:1px solid rgba(127,127,127,.22);"/></div>')
    timing = ""
    if r.get("build_ms") is not None:
        bits = [f"compile {r['build_ms']} ms"]
        if r.get("run_ms") is not None: bits.append(f"run {r['run_ms']} ms")
        timing = f'<span style="opacity:.6;font-size:.85rem;">{" · ".join(bits)}</span>'
    first_error = ""; fe = r.get("first_error")
    if fe:
        context = html.escape(str(fe.get("context") or "")); note = ""
        if not fe.get("in_student_file"):
            note = f'<div style="margin-top:.45rem;font-size:.9rem;">{html.escape(i18n.t("harness_signature_note"))}</div>'
        first_error = '<pre style="overflow:auto;margin:.65rem 0 0;padding:.75rem;border-radius:8px;background:rgba(127,127,127,.09);white-space:pre-wrap;">' + context + "</pre>" + note
    cases = []
    for case in r.get("cases", []):
        passed = bool(case.get("passed")); name = case_label(meta, str(case.get("name", ""))); detail = ""
        if not passed:
            msg = html.escape(message_label(meta, str(case.get("message", ""))) or "")
            detail = f'<div style="margin:.18rem 0 0 1.55rem;opacity:.82;font-size:.9rem;">{msg}'
            if case.get("expected") is not None:
                detail += (' <span style="white-space:nowrap;">'
                           + i18n.t("expected_got", expected=html.escape(str(case.get("expected"))),
                                    actual=html.escape(str(case.get("actual")))) + "</span>")
            detail += "</div>"
        cases.append('<li style="list-style:none;padding:.42rem 0;border-top:1px solid rgba(127,127,127,.12);">'
                     + f'<span aria-hidden="true" style="display:inline-block;width:1.55rem;font-weight:700;">{"✓" if passed else "✕"}</span>'
                     + f"<span>{html.escape(name)}</span>{detail}</li>")
    case_block = ""; test_progress = ""
    if cases:
        raw = r.get("cases", [])
        test_progress = progress_html(sum(bool(c.get("passed")) for c in raw), len(raw), label=i18n.t("tests_label"), accent=accent)
        case_block = '<ul aria-label="' + html.escape(i18n.t("tests_label")) + '" style="padding:0;margin:.65rem 0 0;">' + "".join(cases) + "</ul>"
    extra = []
    if status in ("runtime_error", "solution_error", "harness_error") and r.get("stderr"):
        stderr = html.escape("\n".join(str(r["stderr"]).strip().splitlines()[-8:])); extra.append(f"<details><summary>stderr</summary><pre style=\"white-space:pre-wrap;overflow:auto;\">{stderr}</pre></details>")
    if r.get("stdout"):
        stdout_label = html.escape(i18n.t("your_output"))
        stdout = html.escape("\n".join(str(r["stdout"]).strip().splitlines()[-8:])); extra.append(f'<details><summary>{stdout_label}</summary><pre style="white-space:pre-wrap;overflow:auto;">{stdout}</pre></details>')
    if r.get("work_dir"):
        work = html.escape(str(r["work_dir"]))
        logs = html.escape(i18n.t("logs_line", build=f"{work}/build.log", run=f"{work}/run.log"))
        extra.append("<details><summary>" + html.escape(i18n.t("reproduce_outside_jupyter"))
                     + f'</summary><code>sh {work}/compile.sh</code><div style="margin-top:.35rem;opacity:.75;">{logs}</div></details>')
    hints = meta.get("hints", [])
    if status != "passed" and hints:
        first_hint = html.escape(str(hints[0]))
        extra.append("<details><summary>" + html.escape(i18n.t("need_hint")) + f"</summary><div style=\"margin-top:.45rem;\">{first_hint}</div></details>")
    extras = "".join(f'<div style="margin-top:.55rem;">{x}</div>' for x in extra)
    from .progress import BADGES
    known = {b[0] for b in BADGES}
    badges = "".join('<span style="display:inline-block;margin:.35rem .35rem 0 0;padding:.2rem .48rem;border:1px solid rgba(127,127,127,.25);border-radius:999px;">🏅 '
                     + html.escape(i18n.t(f"badge.{b}.name") if b in known else str(b)) + "</span>"
                     for b in r.get("new_badges", []))
    continue_block = ""
    if status == "passed" and r.get("exercise_id"):
        exercise_id = str(r["exercise_id"])
        params = [f"solved={exercise_id}"]
        if r.get("new_badges"):
            params.append("badge=" + ",".join(str(b) for b in r["new_badges"]))
        url = PAGES_URL + "?" + "&".join(params)
        continue_block = (f'<div style="margin-top:.85rem;"><a class="rk-continue" href="{html.escape(url, quote=True)}" '
                          f'style="display:inline-block;padding:.5rem 1.1rem;border-radius:10px;background:{accent};color:#fff;'
                          f'font-weight:700;text-decoration:none;">{html.escape(i18n.t("continue"))}</a>'
                          f'<div style="margin-top:.4rem;opacity:.75;font-size:.88rem;">{html.escape(i18n.t("continue_help"))}</div></div>')
    return (f'<section role="status" aria-live="polite" style="max-width:860px;border:1px solid rgba(127,127,127,.25);border-left:5px solid {accent};border-radius:12px;padding:1rem 1.15rem;margin:.35rem 0 1rem;line-height:1.45;">'
            f'<header style="display:flex;justify-content:space-between;align-items:baseline;gap:1rem;flex-wrap:wrap;"><div><span style="font-size:.78rem;text-transform:uppercase;letter-spacing:.055em;font-weight:700;">{label}</span><h3 style="font-size:1.1rem;margin:.2rem 0;">{summary}</h3></div>{timing}</header>'
            f'<div style="margin:.5rem 0 .2rem;">{next_text}</div>{preview_block}{first_error}{test_progress}{case_block}{extras}{badges}{continue_block}</section>')
