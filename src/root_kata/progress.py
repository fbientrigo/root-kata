"""Local-only progress and badges. One JSON file, human-readable, no server.

    ~/.root-kata/progress.json   (override with ROOT_KATA_HOME)

{
  "solved": {"cpp-sum-positive": {"at": "2026-08-23T14:02:11", "attempts": 3, "first_try": false}},
  "attempts": {"cpp-root-histogram": 2},
  "badges": {"First Compile": "2026-08-23T14:02:11"}
}
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from .catalog import list_exercises

META_BADGES = [
    ("First Kata", "Solve any exercise", lambda s, ex: len(s) >= 1),
    ("Hat Trick", "Solve three exercises", lambda s, ex: len(s) >= 3),
    ("Track Complete: ROOT basics", "Solve every 'ROOT basics' exercise", lambda s, ex: bool([e for e in ex if e["track"] == "ROOT basics"]) and all(e["id"] in s for e in ex if e["track"] == "ROOT basics")),
    ("Completionist", "Solve every available exercise", lambda s, ex: bool(ex) and all(e["id"] in s for e in ex)),
]


def home() -> Path:
    p = Path(os.environ.get("ROOT_KATA_HOME", "~/.root-kata")).expanduser(); p.mkdir(parents=True, exist_ok=True); return p


def _path() -> Path:
    return home() / "progress.json"


def load() -> dict[str, Any]:
    try: data = json.loads(_path().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError): data = {}
    data.setdefault("solved", {}); data.setdefault("attempts", {}); data.setdefault("badges", {}); return data


def save(data: dict[str, Any]) -> None:
    _path().write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def record(exercise_id: str, result: dict[str, Any]) -> list[str]:
    data = load(); now = datetime.now().replace(microsecond=0).isoformat(); data["attempts"][exercise_id] = data["attempts"].get(exercise_id, 0) + 1; new: list[str] = []
    if result.get("passed") and exercise_id not in data["solved"]:
        attempts = data["attempts"][exercise_id]; data["solved"][exercise_id] = {"at": now, "attempts": attempts, "first_try": attempts == 1}; badge = result.get("_badge")
        if badge and badge not in data["badges"]: data["badges"][badge] = now; new.append(badge)
        if attempts == 1 and "Clean Shot" not in data["badges"]: data["badges"]["Clean Shot"] = now; new.append("Clean Shot")
        solved = set(data["solved"]); exercises = list_exercises()
        for name, _desc, pred in META_BADGES:
            if name not in data["badges"] and pred(solved, exercises): data["badges"][name] = now; new.append(name)
    save(data); return new


def summary() -> dict[str, Any]:
    data = load(); exercises = list_exercises(); rows = []
    for e in exercises:
        s = data["solved"].get(e["id"]); rows.append({**e, "solved": bool(s), "attempts": data["attempts"].get(e["id"], 0), "solved_at": s["at"] if s else None})
    return {"exercises": rows, "badges": data["badges"], "n_solved": len(data["solved"]), "n_total": len(exercises)}


def export(path: str | Path = "root-kata-progress.json") -> Path:
    data = load(); body = json.dumps(data, sort_keys=True); out = {"progress": data, "checksum": hashlib.sha256(body.encode()).hexdigest()[:16], "exported": datetime.now().replace(microsecond=0).isoformat()}; p = Path(path); p.write_text(json.dumps(out, indent=2), encoding="utf-8"); return p
