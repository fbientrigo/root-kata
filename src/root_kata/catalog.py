from __future__ import annotations
import json, os
from pathlib import Path
from typing import Any
REQUIRED_FIELDS={"id","title","track","difficulty","summary","description","requirements","entrypoint","starter","validator","requires"}

def repository_root()->Path:return Path(__file__).resolve().parents[2]
def exercises_root()->Path:
    override=os.environ.get("ROOT_KATA_EXERCISES")
    return Path(override).expanduser().resolve() if override else Path(__file__).resolve().parent/"exercises"
def _load_metadata(path:Path)->dict[str,Any]:
    data=json.loads(path.read_text(encoding="utf-8")); missing=sorted(REQUIRED_FIELDS-data.keys())
    if missing: raise ValueError(f"{path}: missing fields: {', '.join(missing)}")
    if data["id"]!=path.parent.name: raise ValueError(f"{path}: id must match directory name")
    data.setdefault("kind","python")
    if data["kind"] not in ("python","cpp"): raise ValueError(f"{path}: kind must be 'python' or 'cpp'")
    if data["kind"]=="cpp" and "harness" not in data: raise ValueError(f"{path}: cpp exercises need a 'harness' file")
    return data
def list_exercises(*,include_unpublished:bool=False)->list[dict[str,Any]]:
    items=[]
    for metadata_path in sorted(exercises_root().glob("*/exercise.json")):
        data=_load_metadata(metadata_path)
        if not include_unpublished and not data.get("published",True): continue
        item={key:data[key] for key in ("id","title","track","difficulty","summary","requires","kind")}; item["order"]=data.get("order",999); item["topics"]=data.get("topics",[]); item["estimated_minutes"]=data.get("estimated_minutes"); items.append(item)
    return sorted(items,key=lambda item:(item["order"],item["title"]))
def get_exercise(exercise_id:str)->tuple[dict[str,Any],Path]:
    if not exercise_id or any(part in exercise_id for part in ("/","\\","..")): raise KeyError(exercise_id)
    directory=exercises_root()/exercise_id; metadata_path=directory/"exercise.json"
    if not metadata_path.is_file(): raise KeyError(exercise_id)
    return _load_metadata(metadata_path),directory
def exercise_payload(exercise_id:str)->dict[str,Any]:
    metadata,directory=get_exercise(exercise_id); payload=dict(metadata); payload["starter_code"]=(directory/metadata["starter"]).read_text(encoding="utf-8"); return payload
