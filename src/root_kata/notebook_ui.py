from __future__ import annotations

import html
from pathlib import Path
from typing import Any

_ICON = {
    "passed": "✅", "failed": "❌", "compile_error": "🔨", "runtime_error": "💥",
    "runtime_missing": "🚫", "harness_error": "🧩", "timeout": "⏱",
    "solution_error": "💥", "grader_error": "🧩",
}


def statement_text(meta: dict[str, Any], exercise_id: str, solution_path: Path) -> str:
    lines = [f"# {meta['title']}   [{meta['track']} · {meta['difficulty']} · {meta['kind']}]", "", meta["description"], ""]
    lines += [f"  • {r}" for r in meta["requirements"]]
    for ex in meta.get("examples", []):
        lines += ["", f"  input:  {ex['input']}", f"  output: {ex['output']}"]
    if meta.get("badge"):
        lines += ["", f"  🏅 Badge on completion: {meta['badge']}"]
    lines += ["", f"  Edit:  {solution_path}", f"  Then:  rk.check('{exercise_id}')"]
    return "\n".join(lines)


def statement_html(meta: dict[str, Any], exercise_id: str, solution_path: Path, *, cell_ready: bool | None) -> str:
    title = html.escape(str(meta["title"])); track = html.escape(str(meta["track"])); difficulty = html.escape(str(meta["difficulty"])); kind = html.escape(str(meta["kind"]).upper()); description = html.escape(str(meta["description"]))
    estimate = meta.get("estimated_minutes"); estimate_label = f" · ≈{html.escape(str(estimate))} min" if estimate else ""
    requirements = "".join(f"<li>{html.escape(str(item))}</li>" for item in meta["requirements"])
    topics = "".join(f'<span style="display:inline-block;padding:.18rem .45rem;border-radius:999px;background:rgba(127,127,127,.12);font-size:.78rem;">{html.escape(str(topic))}</span>' for topic in meta.get("topics", []))
    topic_row = f'<div style="display:flex;flex-wrap:wrap;gap:.35rem;margin-top:.65rem;">{topics}</div>' if topics else ""
    resources = "".join(f'<li><a href="{html.escape(str(item["url"]), quote=True)}" target="_blank" rel="noopener noreferrer">{html.escape(str(item["label"]))}</a></li>' for item in meta.get("resources", []))
    resource_block = '<details style="margin-top:.75rem;"><summary>References</summary><ul style="margin:.45rem 0 0;padding-left:1.2rem;">' + resources + '</ul></details>' if resources else ""
    examples = ""
    if meta.get("examples"):
        items = []
        for ex in meta["examples"]:
            items.append('<div style="display:grid;grid-template-columns:auto 1fr;gap:.2rem .75rem;">' + f'<span style="opacity:.65">input</span><code>{html.escape(str(ex["input"]))}</code>' + f'<span style="opacity:.65">output</span><code>{html.escape(str(ex["output"]))}</code>' + '</div>')
        examples = '<div style="padding:.8rem 1rem;border:1px solid rgba(127,127,127,.22);border-radius:10px;"><strong style="display:block;margin-bottom:.45rem;">Example</strong>' + "".join(items) + "</div>"
    badge = f'<span title="Badge on completion">🏅 {html.escape(str(meta["badge"]))}</span>' if meta.get("badge") else ""
    if cell_ready is True:
        action = '<strong>Edit the cell below, then press <kbd>Shift</kbd>+<kbd>Enter</kbd>.</strong> Your code is saved automatically.'
    elif cell_ready is False:
        path = html.escape(str(solution_path)); action = f'<strong>Edit <code>{path}</code></strong>, then run <code>rk.check(&quot;{html.escape(exercise_id)}&quot;)</code>.'
    else:
        action = f'<strong>Start here:</strong> <code>rk.start(&quot;{html.escape(exercise_id)}&quot;)</code>'
    return f'''<section style="max-width:860px;border:1px solid rgba(127,127,127,.25);border-radius:14px;padding:1.15rem 1.25rem;margin:.35rem 0 1rem;line-height:1.5;"><header style="margin-bottom:1rem;"><div style="font-size:.78rem;letter-spacing:.055em;text-transform:uppercase;opacity:.65;margin-bottom:.3rem;">{track} · {difficulty} · {kind}{estimate_label}</div><h2 style="font-size:1.35rem;margin:.1rem 0 .45rem;">{title}</h2><div>{description}</div>{topic_row}</header><div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:.75rem;margin:.85rem 0;"><div style="padding:.8rem 1rem;border:1px solid rgba(127,127,127,.22);border-radius:10px;"><strong>Must handle</strong><ul style="margin:.4rem 0 0;padding-left:1.2rem;">{requirements}</ul></div>{examples}</div>{resource_block}<footer style="display:flex;justify-content:space-between;gap:1rem;flex-wrap:wrap;padding-top:.75rem;border-top:1px solid rgba(127,127,127,.18);font-size:.92rem;"><span>{action}</span><span>{badge}</span></footer></section>'''


def format_text(r: dict[str, Any]) -> str:
    icon = _ICON.get(r["status"], "•"); out = [f"{icon} {r['summary']}"]
    if r.get("build_ms") is not None:
        out[0] += f"   (compile {r['build_ms']} ms" + (f", run {r['run_ms']} ms)" if r.get("run_ms") is not None else ")")
    fe = r.get("first_error")
    if fe:
        out += ["", fe["context"] or ""]
        if not fe["in_student_file"]:
            out.append("  (the error is in the harness, which usually means your function signature differs from the one requested)")
    for c in r.get("cases", []):
        line = f"  {'✅' if c['passed'] else '❌'} {c['name']}"
        if not c["passed"]:
            line += f" — {c['message']}"
            if c.get("expected") is not None: line += f"   expected {c['expected']}, got {c['actual']}"
        out.append(line)
    if r["status"] in ("runtime_error", "solution_error", "harness_error") and r.get("stderr"):
        out += ["", "stderr (tail):", *("    " + l for l in r["stderr"].strip().splitlines()[-8:])]
    if r.get("stdout"):
        out += ["", "your output:", *("    " + l for l in r["stdout"].strip().splitlines()[-8:])]
    if r.get("work_dir"):
        out += ["", f"  logs: {r['work_dir']}/build.log, run.log   ·   reproduce: sh {r['work_dir']}/compile.sh"]
    for b in r.get("new_badges", []): out.append(f"\n🏅 New badge: {b}")
    return "\n".join(out)


def progress_html(current: int, total: int, *, label: str = "Tests", accent: str = "#1a7f37") -> str:
    total = max(0, int(total)); current = min(max(0, int(current)), total) if total else 0
    if total == 0: return ""
    safe_label = html.escape(label)
    return ('<div style="margin:.7rem 0 .2rem;"><div style="display:flex;justify-content:space-between;gap:1rem;align-items:baseline;font-size:.88rem;margin-bottom:.28rem;">'
            f'<span style="font-weight:650;">{safe_label}</span><span aria-label="{current} of {total} {safe_label.lower()} passed" style="font-variant-numeric:tabular-nums;opacity:.78;">{current} / {total}</span></div>'
            f'<progress value="{current}" max="{total}" aria-label="{safe_label} passed" style="display:block;width:100%;height:.58rem;accent-color:{accent};">{current} of {total}</progress></div>')
