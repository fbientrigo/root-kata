from __future__ import annotations

import html
from pathlib import Path
from typing import Any

from . import i18n
from .catalog import difficulty_label, kind_label, badge_label

_ICON = {
    "passed": "✅", "failed": "❌", "compile_error": "🔨", "runtime_error": "💥",
    "runtime_missing": "🚫", "harness_error": "🧩", "timeout": "⏱",
    "solution_error": "💥", "grader_error": "🧩",
}


def _summary(result: dict[str, Any], *, lang: str | None = None) -> str:
    """Localized summary: prefer sid+params over the canonical English text."""
    sid = result.get("_sid")
    if sid:
        text = i18n.translate(sid, lang or i18n.get_lang(), **(result.get("_params") or {}))
        if sid == "sum.crashed_signal" and result.get("_params", {}).get("signal") == "SIGSEGV":
            text += i18n.translate("sum.segv_hint", lang or i18n.get_lang())
        return text
    return str(result.get("summary", ""))


def statement_text(meta: dict[str, Any], exercise_id: str, solution_path: Path) -> str:
    lines = [f"# {meta['title']}   [{meta['track']} · {difficulty_label(meta['difficulty'])} · {kind_label(meta['kind'])}]", "", meta["description"], ""]
    lines += [f"  • {r}" for r in meta["requirements"]]
    for ex in meta.get("examples", []):
        lines += ["", f"  {i18n.t('input_label')}:  {ex['input']}", f"  {i18n.t('output_label')}: {ex['output']}"]
    badge = badge_label(meta.get("badge"))
    if badge:
        lines += ["", "  " + i18n.t("badge_line", badge=badge)]
    lines += ["", i18n.t("statement_edit_line", path=solution_path), i18n.t("statement_then_line", exercise_id=exercise_id)]
    return "\n".join(lines)


def _html_with_code(template_result: str) -> str:
    """Escape a translated sentence; \x00/\x01 sentinels become <code> tags."""
    escaped = html.escape(template_result).replace("&#x0;", "").replace("\x00", "<code>").replace("\x01", "</code>")
    return "<strong>" + escaped + "</strong>"


def statement_html(meta: dict[str, Any], exercise_id: str, solution_path: Path, *, cell_ready: bool | None) -> str:
    title = html.escape(str(meta["title"])); track = html.escape(str(meta["track"])); difficulty = html.escape(difficulty_label(meta["difficulty"])); kind = html.escape(kind_label(meta["kind"]).upper()); description = html.escape(str(meta["description"]))
    estimate = meta.get("estimated_minutes"); estimate_label = f" · ≈{html.escape(str(estimate))} min" if estimate else ""
    requirements = "".join(f"<li>{html.escape(str(item))}</li>" for item in meta["requirements"])
    topics = "".join(f'<span style="display:inline-block;padding:.18rem .45rem;border-radius:999px;background:rgba(127,127,127,.12);font-size:.78rem;">{html.escape(str(topic))}</span>' for topic in meta.get("topics", []))
    topic_row = f'<div style="display:flex;flex-wrap:wrap;gap:.35rem;margin-top:.65rem;">{topics}</div>' if topics else ""
    resources = "".join(f'<li><a href="{html.escape(str(item["url"]), quote=True)}" target="_blank" rel="noopener noreferrer">{html.escape(str(item["label"]))}</a></li>' for item in meta.get("resources", []))
    resource_block = ('<details style="margin-top:.75rem;"><summary>' + html.escape(i18n.t("references")) + '</summary><ul style="margin:.45rem 0 0;padding-left:1.2rem;">' + resources + "</ul></details>") if resources else ""
    examples = ""
    if meta.get("examples"):
        items = []
        for ex in meta["examples"]:
            items.append('<div style="display:grid;grid-template-columns:auto 1fr;gap:.2rem .75rem;">'
                         + f'<span style="opacity:.65">{html.escape(i18n.t("input_label"))}</span><code>{html.escape(str(ex["input"]))}</code>'
                         + f'<span style="opacity:.65">{html.escape(i18n.t("output_label"))}</span><code>{html.escape(str(ex["output"]))}</code>'
                         + "</div>")
        examples = ('<div style="padding:.8rem 1rem;border:1px solid rgba(127,127,127,.22);border-radius:10px;"><strong style="display:block;margin-bottom:.45rem;">'
                    + html.escape(i18n.t("example")) + "</strong>" + "".join(items) + "</div>")
    badge = f'<span title="{html.escape(i18n.t("badge_on_completion"))}">🏅 {html.escape(badge_label(meta.get("badge")) or "")}</span>' if meta.get("badge") else ""
    if cell_ready is True:
        action = "<strong>" + html.escape(i18n.t("edit_cell_below", key1="Shift", key2="Enter")) + "</strong>"
    elif cell_ready is False:
        action = _html_with_code(i18n.t("edit_file_then_check", path=f"\x00{solution_path}\x01", cmd=f'\x00rk.check("{exercise_id}")\x01'))
    else:
        action = _html_with_code(i18n.t("start_here", cmd=f'\x00rk.start("{exercise_id}")\x01'))
    return (f'<section style="max-width:860px;border:1px solid rgba(127,127,127,.25);border-radius:14px;padding:1.15rem 1.25rem;margin:.35rem 0 1rem;line-height:1.5;">'
            f'<header style="margin-bottom:1rem;"><div style="font-size:.78rem;letter-spacing:.055em;text-transform:uppercase;opacity:.65;margin-bottom:.3rem;">{track} · {difficulty} · {kind}{estimate_label}</div>'
            f'<h2 style="font-size:1.35rem;margin:.1rem 0 .45rem;">{title}</h2><div>{description}</div>{topic_row}</header>'
            f'<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:.75rem;margin:.85rem 0;">'
            f'<div style="padding:.8rem 1rem;border:1px solid rgba(127,127,127,.22);border-radius:10px;"><strong>{html.escape(i18n.t("must_handle"))}</strong><ul style="margin:.4rem 0 0;padding-left:1.2rem;">{requirements}</ul></div>{examples}</div>'
            f'{resource_block}<footer style="display:flex;justify-content:space-between;gap:1rem;flex-wrap:wrap;padding-top:.75rem;border-top:1px solid rgba(127,127,127,.18);font-size:.92rem;"><span>{action}</span><span>{badge}</span></footer></section>')


def format_text(r: dict[str, Any]) -> str:
    from .catalog import case_label, message_label
    icon = _ICON.get(r["status"], "•"); out = [f"{icon} {_summary(r)}"]
    if r.get("build_ms") is not None:
        out[0] += f"   (compile {r['build_ms']} ms" + (f", run {r['run_ms']} ms)" if r.get("run_ms") is not None else ")")
    fe = r.get("first_error")
    if fe:
        out += ["", fe["context"] or ""]
        if not fe["in_student_file"]:
            out.append("  " + i18n.t("harness_signature_note_text"))
    meta = r.get("_meta", {})
    for c in r.get("cases", []):
        name = case_label(meta, str(c["name"]))
        line = f"  {'✅' if c['passed'] else '❌'} {name}"
        if not c["passed"]:
            line += f" — {message_label(meta, str(c['message']))}"
            if c.get("expected") is not None:
                line += i18n.t("expected_got_text", expected=c["expected"], actual=c["actual"])
        out.append(line)
    if r["status"] in ("runtime_error", "solution_error", "harness_error") and r.get("stderr"):
        out += ["", i18n.t("stderr_tail"), *("    " + l for l in str(r["stderr"]).strip().splitlines()[-8:])]
    if r.get("stdout"):
        out += ["", i18n.t("your_output") + ":", *("    " + l for l in str(r["stdout"]).strip().splitlines()[-8:])]
    if r.get("preview"):
        out += ["", i18n.t("preview_saved_text", path=r["preview"]["path"])]
    if r.get("work_dir"):
        out += ["", i18n.t("logs_reproduce_text", work=r["work_dir"])]
    from .progress import BADGES
    known = {b[0] for b in BADGES}
    for b in r.get("new_badges", []):
        label = i18n.t(f"badge.{b}.name") if b in known else b
        out.append("\n🏅 " + i18n.t("new_badge") + " " + label)
    return "\n".join(out)


def progress_html(current: int, total: int, *, label: str | None = None, accent: str = "#1a7f37") -> str:
    total = max(0, int(total)); current = min(max(0, int(current)), total) if total else 0
    if total == 0: return ""
    safe_label = html.escape(label if label is not None else i18n.t("tests_label"))
    return ('<div style="margin:.7rem 0 .2rem;"><div style="display:flex;justify-content:space-between;gap:1rem;align-items:baseline;font-size:.88rem;margin-bottom:.28rem;">'
            f'<span style="font-weight:650;">{safe_label}</span><span aria-label="{current} of {total} {safe_label.lower()}" style="font-variant-numeric:tabular-nums;opacity:.78;">{current} / {total}</span></div>'
            f'<progress value="{current}" max="{total}" aria-label="{safe_label}" style="display:block;width:100%;height:.58rem;accent-color:{accent};">{current} of {total}</progress></div>')
