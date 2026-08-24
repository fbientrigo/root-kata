"""Local-only progress and badges. One JSON file, human-readable, no server.

    ~/.root-kata/progress.json   (override with ROOT_KATA_HOME)

{
  "solved": {"cpp-sum-positive": {"at": "2026-08-23T14:02:11", "attempts": 3, "first_try": false}},
  "attempts": {"cpp-root-histogram": 2},
  "badges": {"first_kata": "2026-08-23T14:02:11"}
}

Badge keys are stable ids (never localized). Older files that stored English
badge names are migrated once on load; retired badges are dropped.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from .catalog import list_exercises

# (stable id, description-id, predicate(solved_ids, exercises))
BADGES: list[tuple[str, str, Callable[[set[str], list[dict[str, Any]]], bool]]] = [
    ("first_kata", "badge.first_kata.desc", lambda solved, ex: len(solved) >= 1),
    ("first_root_histogram", "badge.first_root_histogram.desc", lambda solved, ex: "cpp-root-histogram" in solved),
    ("basics_complete", "badge.basics_complete.desc", lambda solved, ex: bool(ex) and {e["id"] for e in ex} <= solved),
]

# Migration: pre-i18n progress files used English display names as badge keys.
_OLD_BADGE_IDS = {
    "First Kata": "first_kata",
    "Histogrammer": "first_root_histogram",
    "First Compile": None,  # retired: per-exercise noise
    "Cut Maker": None,
    "Clean Shot": None,     # retired: solving on the first try is not rewarded
    "Hat Trick": "basics_complete",
    "Track Complete: ROOT basics": "basics_complete",
    "Completionist": "basics_complete",
}


def home() -> Path:
    p = Path(os.environ.get("ROOT_KATA_HOME", "~/.root-kata")).expanduser(); p.mkdir(parents=True, exist_ok=True); return p


def _path() -> Path:
    return home() / "progress.json"


def load() -> dict[str, Any]:
    try:
        raw = _path().read_text(encoding="utf-8")
        data = json.loads(raw)
        if isinstance(data, dict):
            data, changed = _migrate(data)
            if changed:
                save(data)
        else:
            data = {}
    except (OSError, json.JSONDecodeError):
        data = {}
    data.setdefault("solved", {}); data.setdefault("attempts", {}); data.setdefault("badges", {}); return data


def _migrate(data: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    """Map legacy English badge names to stable ids; drop retired ones."""
    badges = data.get("badges")
    if not isinstance(badges, dict):
        return data, False
    known = {b[0] for b in BADGES}
    migrated: dict[str, str] = {}
    changed = False
    for name, at in badges.items():
        badge_id = name if name in known else _OLD_BADGE_IDS.get(name)
        if badge_id is None or badge_id != name:
            changed = True
            if badge_id is None:
                continue
        migrated.setdefault(badge_id, at)  # keep earliest timestamp
    if changed:
        data["badges"] = migrated
    return data, changed


def save(data: dict[str, Any]) -> None:
    _path().write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def record(exercise_id: str, result: dict[str, Any]) -> list[str]:
    """Update attempts/solved; return newly earned *badge ids*."""
    data = load(); now = datetime.now().replace(microsecond=0).isoformat(); data["attempts"][exercise_id] = data["attempts"].get(exercise_id, 0) + 1; new: list[str] = []
    if result.get("passed") and exercise_id not in data["solved"]:
        attempts = data["attempts"][exercise_id]; data["solved"][exercise_id] = {"at": now, "attempts": attempts, "first_try": attempts == 1}
        solved = set(data["solved"]); exercises = list_exercises()
        for badge_id, _desc, pred in BADGES:
            if badge_id not in data["badges"] and pred(solved, exercises): data["badges"][badge_id] = now; new.append(badge_id)
    save(data); return new


def summary() -> dict[str, Any]:
    data = load(); exercises = list_exercises(); rows = []
    for e in exercises:
        s = data["solved"].get(e["id"]); rows.append({**e, "solved": bool(s), "attempts": data["attempts"].get(e["id"], 0), "solved_at": s["at"] if s else None})
    return {"exercises": rows, "badges": data["badges"], "n_solved": len(data["solved"]), "n_total": len(exercises)}


def export(path: str | Path = "root-kata-progress.json") -> Path:
    data = load(); body = json.dumps(data, sort_keys=True); out = {"progress": data, "checksum": hashlib.sha256(body.encode()).hexdigest()[:16], "exported": datetime.now().replace(microsecond=0).isoformat()}; p = Path(path); p.write_text(json.dumps(out, indent=2), encoding="utf-8"); return p
