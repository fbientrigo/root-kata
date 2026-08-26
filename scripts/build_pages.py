#!/usr/bin/env python3
"""Build the zero-dependency GitHub Pages catalog from exercise metadata.

Spanish is the primary language (docs/index.html); English lives under
docs/en/. Both are fully generated, static, and share one stylesheet/script.
"""
from __future__ import annotations

import html
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXERCISES = ROOT / "src" / "root_kata" / "exercises"
DOCS = ROOT / "docs"

UI = {
    "es": {
        "tagline": "práctica corta de C++/ROOT en Jupyter",
        "all_katas": "← Todos los katas",
        "open_in_jupyter": "Abrir en Jupyter",
        "read_problem": "Leer problema",
        "problem": "Problema",
        "example": "Ejemplo",
        "input": "Entrada",
        "output": "Salida",
        "requirements": "Requisitos",
        "practices": "Qué practicas",
        "references": "Referencias",
        "implement": "Implementa",
        "start_title": "Empieza en Jupyter",
        "start_help": "Abre tu Jupyter local y pega el comando de abajo. El botón intenta copiarlo.",
        "easy": "Fácil",
        "introductory": "Introductorio",
        "intermediate": "Intermedio",
        "hard": "Difícil",
        "difficulty_filter": "Dificultad",
        "all_difficulties": "Todas",
        "showing": "{visible} de {total} ejercicios",
        "minutes": "≈ {n} min",
        "local_note": "<strong>Abrir en Jupyter</strong><span>El botón abre el cuaderno del kata en <code>127.0.0.1:8888</code> (requiere <code>root-kata lab</code> corriendo) e intenta copiar el comando.</span>",
        "hero_eyebrow": "Ruta inicial desde cero",
        "hero_title": "Empieza pequeño. Llega a ROOT entendiendo cada paso.",
        "hero_text": "Comienza con C++ elemental y avanza hasta una primera operación ROOT. Cada kata introduce una sola idea útil.",
        "flow": ["1 · imprimir", "2 · arreglos", "3 · analizar"],
        "your_progress": "Tu progreso",
        "completed": "Completado",
        "view_problem": "Ver problema",
        "exercises": "Ejercicios",
        "footer": "Prototipo educativo no oficial · sin cuentas · corre en tu máquina",
    },
    "en": {
        "tagline": "short C++/ROOT practice in Jupyter",
        "all_katas": "← All katas",
        "open_in_jupyter": "Open in Jupyter",
        "read_problem": "Read problem",
        "problem": "Problem",
        "example": "Example",
        "input": "Input",
        "output": "Output",
        "requirements": "Requirements",
        "practices": "What this practices",
        "references": "References",
        "implement": "Implement",
        "start_title": "Start in Jupyter",
        "start_help": "Open your local Jupyter and paste the command below. The button tries to copy it for you.",
        "easy": "Easy",
        "introductory": "Introductory",
        "intermediate": "Intermediate",
        "hard": "Hard",
        "difficulty_filter": "Difficulty",
        "all_difficulties": "All",
        "showing": "{visible} of {total} exercises",
        "minutes": "≈ {n} min",
        "local_note": "<strong>Open in Jupyter</strong><span>The button opens the kata notebook at <code>127.0.0.1:8888</code> (needs <code>root-kata lab</code> running) and tries to copy the command.</span>",
        "hero_eyebrow": "Starter path from zero",
        "hero_title": "Start small. Reach ROOT understanding every step.",
        "hero_text": "Begin with elementary C++ and advance to a first ROOT operation. Each kata introduces one useful idea.",
        "flow": ["1 · print", "2 · arrays", "3 · analyze"],
        "your_progress": "Your progress",
        "completed": "Completed",
        "view_problem": "View problem",
        "exercises": "Exercises",
        "footer": "Unofficial educational prototype · no accounts · runs on your machine",
    },
}


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def load_exercises() -> list[tuple[dict, Path]]:
    rows: list[tuple[dict, Path]] = []
    for path in EXERCISES.glob("*/exercise.json"):
        meta = json.loads(path.read_text(encoding="utf-8"))
        if not meta.get("published", True):
            continue
        rows.append((meta, path.parent))
    return sorted(rows, key=lambda row: (row[0].get("order", 999), row[0]["title"]))


def view(meta: dict, lang: str) -> dict:
    """Exercise metadata overlaid with the requested display language."""
    out = dict(meta)
    overlay = meta.get(lang)
    if lang != "en" and isinstance(overlay, dict):
        for field in ("title", "track", "difficulty", "summary", "description", "topics", "learning_goal"):
            if field in overlay:
                out[field] = overlay[field]
        if "requirements" in overlay:
            out["requirements"] = overlay["requirements"]
        if "examples" in overlay:
            out["examples"] = [{**base, **extra} for base, extra in zip(meta.get("examples", []), overlay["examples"])]
    # Filter by the stable English metadata key, even when the visible label is localized.
    difficulty_key = str(meta.get("difficulty", "")).lower()
    out["difficulty_key"] = difficulty_key
    if difficulty_key in {"introductory", "easy", "intermediate", "hard"}:
        out["difficulty_label"] = UI[lang][difficulty_key]
    else:
        out["difficulty_label"] = str(out.get("difficulty", ""))
    return out


def chips(values: list[str]) -> str:
    return "".join(f'<span class="chip">{esc(v)}</span>' for v in values)


def jupyter_command(exercise_id: str) -> str:
    return f'import root_kata as rk\nrk.start("{exercise_id}")'


def notebook_url(exercise_id: str) -> str:
    return f"http://127.0.0.1:8888/lab/tree/notebooks/{exercise_id}.ipynb"


def shell(
    *,
    lang: str,
    title: str,
    body: str,
    description: str,
    asset_prefix: str = "",
    home_href: str = "index.html",
    switch_href: str = "index.html",
) -> str:
    """Render one page with explicit paths from that page to shared assets/home.

    Asset depth and language location are independent. Keeping them explicit
    prevents nested pages from accidentally generating paths such as
    `problems/styles.css` or `en/styles.css`.
    """
    ui = UI[lang]
    other = "es" if lang == "en" else "en"
    return f'''<!doctype html>
<html lang="{lang}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="{esc(description)}">
  <title>{esc(title)} · ROOT Kata</title>
  <link rel="stylesheet" href="{asset_prefix}styles.css">
</head>
<body>
  <header class="site-header">
    <a class="brand" href="{home_href}">ROOT Kata</a>
    <span>{esc(ui["tagline"])}</span>
    <nav class="lang-switch" aria-label="Language"><a href="{switch_href}" lang="{other}" hreflang="{other}">{other.upper()}</a></nav>
  </header>
  {body}
  <footer class="site-footer">{ui["footer"]}</footer>
  <script src="{asset_prefix}site.js" defer></script>
</body>
</html>
'''


def kata_row(meta_view: dict, lang: str) -> str:
    eid = meta_view["id"]
    ui = UI[lang]
    return f'''
      <article class="kata-row" data-eid="{esc(eid)}" data-difficulty="{esc(meta_view[\'difficulty_key\'])}">
        <div class="row-status"><span class="status-icon" aria-hidden="true">○</span><span class="visually-hidden status-label"></span></div>
        <div class="row-body">
          <div class="row-topline"><span class="difficulty">{esc(meta_view['difficulty_label'])}</span><span aria-hidden="true">·</span><span>{esc(ui['minutes'].format(n=meta_view.get('estimated_minutes', '?')))}</span></div>
          <h2>{esc(meta_view['title'])}</h2>
          <p>{esc(meta_view['summary'])}</p>
          <div class="chips">{chips(meta_view.get('topics', []))}</div>
        </div>
        <div class="row-actions">
          <a class="button primary jupyter-link" href="{esc(notebook_url(eid))}" target="_blank" rel="noopener" data-command="{esc(jupyter_command(eid))}">{esc(ui['open_in_jupyter'])}</a>
          <a class="button secondary problem-link" href="problems/{esc(eid)}.html">{esc(ui['view_problem'])}</a>
          <span class="completed-label" hidden>{esc(ui['completed'])}</span>
        </div>
      </article>'''


def build_index(exercises: list[tuple[dict, Path]], lang: str) -> None:
    ui = UI[lang]
    page_prefix = "" if lang == "es" else "en/"
    asset_prefix = "" if lang == "es" else "../"
    rows = "".join(kata_row(view(meta, lang), lang) for meta, _ in exercises)
    flow = f'<span>{ui["flow"][0]}</span><span aria-hidden="true">→</span><span>{ui["flow"][1]}</span><span aria-hidden="true">→</span><span>{ui["flow"][2]}</span>'
    total = len(exercises)
    present_difficulties = {str(meta.get("difficulty", "")).lower() for meta, _ in exercises}
    difficulty_options = [f'<option value="all">{esc(ui["all_difficulties"])}</option>']
    for key in ("introductory", "easy", "intermediate", "hard"):
        if key in present_difficulties:
            difficulty_options.append(f'<option value="{key}">{esc(ui[key])}</option>')
    difficulty_options_html = "".join(difficulty_options)
    body = f'''
  <main class="home">
    <section class="hero">
      <h1>{esc(ui["hero_title"])}</h1>
      <p>{esc(ui["hero_text"])}</p>
      <div class="flow" aria-label="Learning path">{flow}</div>
    </section>

    <section class="progress-panel" data-total="{total}" aria-labelledby="progress-title">
      <h2 id="progress-title">{esc(ui["your_progress"])}</h2>
      <div class="progress-row">
        <progress id="overall-progress" value="0" max="{total}" aria-hidden="true"></progress>
        <span id="progress-count" role="status" aria-live="polite">0 / {total}</span>
      </div>
      <ul id="badge-list" class="badge-list"></ul>
    </section>

    <div class="catalog-tools">
      <label for="difficulty-filter">{esc(ui["difficulty_filter"])}</label>
      <select id="difficulty-filter">
        {difficulty_options_html}
      </select>
      <span id="filter-count" role="status" aria-live="polite">{esc(ui["showing"].format(visible=total, total=total))}</span>
    </div>

    <section class="kata-list" aria-label="{esc(ui["exercises"])}">
      {rows}
    </section>

    <aside class="local-note">{ui["local_note"]}</aside>
  </main>'''
    target = DOCS / page_prefix if lang != "es" else DOCS
    target.mkdir(parents=True, exist_ok=True)
    switch = "en/index.html" if lang == "es" else "../index.html"
    (target / "index.html").write_text(
        shell(
            lang=lang,
            title="Katas",
            body=body,
            description=ui["hero_text"],
            asset_prefix=asset_prefix,
            home_href="index.html",
            switch_href=switch,
        ),
        encoding="utf-8",
    )


def build_problem(meta: dict, directory: Path, lang: str) -> None:
    eid = meta["id"]
    ui = UI[lang]
    v = view(meta, lang)
    page_prefix = "" if lang == "es" else "en/"
    asset_prefix = "../" if lang == "es" else "../../"
    home_href = "../index.html"
    examples = []
    for item in v.get("examples", []):
        explanation = f'<p>{esc(item["explanation"])}</p>' if item.get("explanation") else ""
        examples.append(f'''
        <div class="example-box">
          <div><span>{esc(ui["input"])}</span><code>{esc(item['input'])}</code></div>
          <div><span>{esc(ui["output"])}</span><code>{esc(item['output'])}</code></div>
          {explanation}
        </div>''')
    requirements = "".join(f"<li>{esc(x)}</li>" for x in v.get("requirements", []))
    resources = "".join(
        f'<li><a href="{esc(item["url"])}" target="_blank" rel="noopener">{esc(item["label"])}</a></li>'
        for item in v.get("resources", [])
    )
    runtime = "ROOT + C++" if v.get("requires") else "C++17"
    command = jupyter_command(eid)
    body = f'''
  <main class="problem-layout">
    <a class="back-link" href="{home_href}">{esc(ui["all_katas"])}</a>
    <article class="problem">
      <header class="problem-header">
        <div class="problem-meta">
          <span class="difficulty">{esc(v['difficulty_label'])}</span>
          <span>{esc(ui['minutes'].format(n=v.get('estimated_minutes', '?')))}</span>
          <span>{runtime}</span>
        </div>
        <h1>{esc(v['title'])}</h1>
        <p class="lead">{esc(v['summary'])}</p>
        <div class="chips">{chips(v.get('topics', []))}</div>
      </header>

      <section>
        <h2>{esc(ui["problem"])}</h2>
        <p>{esc(v['description'])}</p>
        <div class="contract"><span>{esc(ui["implement"])}</span><code>{esc(v['entrypoint'])}(…)</code></div>
      </section>

      <section>
        <h2>{esc(ui["example"])}</h2>
        {''.join(examples)}
      </section>

      <section>
        <h2>{esc(ui["requirements"])}</h2>
        <ul>{requirements}</ul>
      </section>

      <section>
        <h2>{esc(ui["practices"])}</h2>
        <p>{esc(v.get('learning_goal', ''))}</p>
      </section>

      <section>
        <h2>{esc(ui["references"])}</h2>
        <ul class="resource-list">{resources}</ul>
      </section>

      <section class="start-panel">
        <div>
          <h2>{esc(ui["start_title"])}</h2>
          <p>{esc(ui["start_help"])}</p>
          <pre><code>{esc(command)}</code></pre>
        </div>
        <a class="button primary large jupyter-link" href="{esc(notebook_url(eid))}" target="_blank" rel="noopener" data-command="{esc(command)}">{esc(ui['open_in_jupyter'])}</a>
      </section>
    </article>
  </main>'''
    target = DOCS / page_prefix / "problems"
    target.mkdir(parents=True, exist_ok=True)
    switch = f"../en/problems/{eid}.html" if lang == "es" else f"../../problems/{eid}.html"
    (target / f"{eid}.html").write_text(
        shell(
            lang=lang,
            title=v["title"],
            body=body,
            description=v["summary"],
            asset_prefix=asset_prefix,
            home_href=home_href,
            switch_href=switch,
        ),
        encoding="utf-8",
    )
    source = directory / meta.get("problem_markdown", "problem.md")
    if source.is_file():
        shutil.copyfile(source, target / f"{eid}.md")


def main() -> None:
    for stale_dir in (DOCS / "problems", DOCS / "en"):
        if stale_dir.exists():
            shutil.rmtree(stale_dir)
    exercises = load_exercises()
    for lang in ("es", "en"):
        build_index(exercises, lang)
        for meta, directory in exercises:
            build_problem(meta, directory, lang)
    print(f"Built {len(exercises)} public katas in ES + EN under {DOCS}")


if __name__ == "__main__":
    main()
