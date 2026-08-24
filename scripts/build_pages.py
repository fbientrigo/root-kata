#!/usr/bin/env python3
"""Build the zero-dependency GitHub Pages catalog from exercise metadata."""
from __future__ import annotations

import html
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXERCISES = ROOT / "src" / "root_kata" / "exercises"
DOCS = ROOT / "docs"
PROBLEMS = DOCS / "problems"


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


def chips(values: list[str]) -> str:
    return "".join(f'<span class="chip">{esc(v)}</span>' for v in values)


def jupyter_command(exercise_id: str) -> str:
    return f'import root_kata as rk\nrk.start("{exercise_id}")'


def shell(*, title: str, body: str, description: str) -> str:
    return f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="{esc(description)}">
  <title>{esc(title)} · ROOT Kata</title>
  <link rel="stylesheet" href="{('../' if title != 'Katas' else '')}styles.css">
</head>
<body>
  <header class="site-header">
    <a class="brand" href="{('../' if title != 'Katas' else '')}index.html">ROOT Kata</a>
    <span>short C++/ROOT practice in Jupyter</span>
  </header>
  {body}
  <footer class="site-footer">Unofficial educational prototype · no accounts · runs on your machine</footer>
  <script src="{('../' if title != 'Katas' else '')}site.js" defer></script>
</body>
</html>
'''


def build_index(exercises: list[tuple[dict, Path]]) -> None:
    cards = []
    for meta, _ in exercises:
        eid = meta["id"]
        runtime = "ROOT" if meta.get("requires") else "C++"
        cards.append(f'''
      <article class="kata-card">
        <div class="card-topline">
          <span class="step">{esc(meta.get('order', ''))}</span>
          <span class="difficulty">{esc(meta['difficulty'])}</span>
          <span class="runtime">{runtime}</span>
        </div>
        <h2>{esc(meta['title'])}</h2>
        <p>{esc(meta['summary'])}</p>
        <div class="chips">{chips(meta.get('topics', [])[:4])}</div>
        <div class="card-meta">≈ {esc(meta.get('estimated_minutes', '?'))} min · {esc(meta['track'])}</div>
        <div class="card-actions">
          <a class="button primary jupyter-link" href="http://127.0.0.1:8888/lab" target="_blank" rel="noopener" data-command="{esc(jupyter_command(eid))}">Open in Jupyter</a>
          <a class="button secondary" href="problems/{esc(eid)}.html">Read problem</a>
        </div>
      </article>''')

    body = f'''
  <main class="home">
    <section class="hero">
      <p class="eyebrow">3-step starter track</p>
      <h1>Practice the operations you will actually reuse.</h1>
      <p>Read a small problem, open it in Jupyter, edit one function, run the visible tests. No account and no cloud runner.</p>
      <div class="flow" aria-label="Learning path">
        <span>1 · accumulate</span><span aria-hidden="true">→</span><span>2 · select</span><span aria-hidden="true">→</span><span>3 · histogram</span>
      </div>
    </section>

    <section class="kata-grid" aria-label="Katas">
      {''.join(cards)}
    </section>

    <aside class="local-note">
      <strong>Open in Jupyter</strong>
      <span>The button opens <code>127.0.0.1:8888/lab</code> and copies the kata command when your browser allows it. Jupyter must already be running locally.</span>
    </aside>
  </main>'''
    (DOCS / "index.html").write_text(shell(title="Katas", body=body, description="Three short ROOT Kata exercises that open in local Jupyter."), encoding="utf-8")


def build_problem(meta: dict, directory: Path) -> None:
    eid = meta["id"]
    examples = []
    for item in meta.get("examples", []):
        explanation = f'<p>{esc(item["explanation"])}</p>' if item.get("explanation") else ""
        examples.append(f'''
        <div class="example-box">
          <div><span>Input</span><code>{esc(item['input'])}</code></div>
          <div><span>Output</span><code>{esc(item['output'])}</code></div>
          {explanation}
        </div>''')
    requirements = "".join(f"<li>{esc(x)}</li>" for x in meta.get("requirements", []))
    resources = "".join(
        f'<li><a href="{esc(item["url"])}" target="_blank" rel="noopener">{esc(item["label"])}</a></li>'
        for item in meta.get("resources", [])
    )
    runtime = "ROOT + C++" if meta.get("requires") else "C++17"
    command = jupyter_command(eid)
    body = f'''
  <main class="problem-layout">
    <a class="back-link" href="../index.html">← All katas</a>
    <article class="problem">
      <header class="problem-header">
        <div class="problem-meta">
          <span class="difficulty">{esc(meta['difficulty'])}</span>
          <span>≈ {esc(meta.get('estimated_minutes', '?'))} min</span>
          <span>{runtime}</span>
        </div>
        <h1>{esc(meta['title'])}</h1>
        <p class="lead">{esc(meta['summary'])}</p>
        <div class="chips">{chips(meta.get('topics', []))}</div>
      </header>

      <section>
        <h2>Problem</h2>
        <p>{esc(meta['description'])}</p>
        <div class="contract"><span>Implement</span><code>{esc(meta['entrypoint'])}(…)</code></div>
      </section>

      <section>
        <h2>Example</h2>
        {''.join(examples)}
      </section>

      <section>
        <h2>Requirements</h2>
        <ul>{requirements}</ul>
      </section>

      <section>
        <h2>What this practices</h2>
        <p>{esc(meta.get('learning_goal', ''))}</p>
      </section>

      <section>
        <h2>References</h2>
        <ul class="resource-list">{resources}</ul>
      </section>

      <section class="start-panel">
        <div>
          <h2>Start in Jupyter</h2>
          <p>Open your local Jupyter and paste the command below. The button tries to copy it for you.</p>
          <pre><code>{esc(command)}</code></pre>
        </div>
        <a class="button primary large jupyter-link" href="http://127.0.0.1:8888/lab" target="_blank" rel="noopener" data-command="{esc(command)}">Open in Jupyter</a>
      </section>

      <p class="source-link"><a href="{esc(eid)}.md">Markdown problem source</a></p>
    </article>
  </main>'''
    (PROBLEMS / f"{eid}.html").write_text(shell(title=meta["title"], body=body, description=meta["summary"]), encoding="utf-8")
    source = directory / meta.get("problem_markdown", "problem.md")
    if source.is_file():
        shutil.copyfile(source, PROBLEMS / f"{eid}.md")


def main() -> None:
    DOCS.mkdir(exist_ok=True)
    PROBLEMS.mkdir(exist_ok=True)
    for old in PROBLEMS.glob("cpp-*.html"):
        old.unlink()
    exercises = load_exercises()
    build_index(exercises)
    for meta, directory in exercises:
        build_problem(meta, directory)
    print(f"Built {len(exercises)} public kata pages in {DOCS}")


if __name__ == "__main__":
    main()
