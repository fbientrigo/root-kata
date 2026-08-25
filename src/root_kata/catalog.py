from __future__ import annotations
import json, os
from pathlib import Path
from typing import Any
from . import i18n
REQUIRED_FIELDS={"id","title","track","difficulty","summary","description","requirements","entrypoint","starter","validator","requires"}
LOCALIZED_FIELDS=("title","track","difficulty","summary","description","requirements","hints","topics","examples","learning_goal","preview")
_DEFAULT_MESSAGE_KEYS={"Values differ":"val.values_differ","Values are not close":"val.not_close","Passed":"val.case_passed"}

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
        item={key:data[key] for key in ("id","title","track","difficulty","summary","requires","kind")}
        if isinstance(data.get("es"),dict): item["es"]=data["es"]
        item["order"]=data.get("order",999); item["topics"]=data.get("topics",[]); item["estimated_minutes"]=data.get("estimated_minutes"); items.append(item)
    return sorted(items,key=lambda item:(item["order"],item["title"]))
def get_exercise(exercise_id:str)->tuple[dict[str,Any],Path]:
    if not exercise_id or any(part in exercise_id for part in ("/","\\","..")): raise KeyError(exercise_id)
    directory=exercises_root()/exercise_id; metadata_path=directory/"exercise.json"
    if not metadata_path.is_file(): raise KeyError(exercise_id)
    return _load_metadata(metadata_path),directory
def exercise_payload(exercise_id:str)->dict[str,Any]:
    metadata,directory=get_exercise(exercise_id); payload=dict(metadata); payload["starter_code"]=(directory/metadata["starter"]).read_text(encoding="utf-8"); return payload

def localized(meta:dict[str,Any],lang:str|None=None)->dict[str,Any]:
    """Metadata view with student-facing copy in `lang` (default: active).

    Internal ids never change; only presentation fields are overlaid from the
    exercise's own localized object.
    """
    lang=lang or i18n.get_lang(); out=dict(meta); overlay=meta.get(lang)
    if lang!="en" and isinstance(overlay,dict):
        for field in LOCALIZED_FIELDS:
            if field in overlay: out[field]=overlay[field]
        if "examples" in overlay:
            out["examples"]=[{**base,**(extra or {})} for base,extra in zip(meta.get("examples",[]),overlay["examples"])]
    return out

def _label_or_raw(key:str,raw:str)->str:
    if key in i18n._STRINGS.get(i18n.get_lang(),{}) or key in i18n._STRINGS["en"]: return i18n.t(key)
    return raw
def difficulty_label(difficulty:str)->str:return _label_or_raw(f"difficulty.{str(difficulty).lower()}",difficulty)
def kind_label(kind:str)->str:return _label_or_raw(f"kind.{kind}",kind)
def badge_label(badge_id:str|None)->str|None:return i18n.t(f"badge.{badge_id}.name") if badge_id else None
def case_label(meta:dict[str,Any],name:str)->str:
    overlay=meta.get(i18n.get_lang(),{})
    return overlay.get("cases",{}).get(name,name) if isinstance(overlay,dict) else name
def message_label(meta:dict[str,Any],message:str|None)->str|None:
    if message is None: return None
    key=_DEFAULT_MESSAGE_KEYS.get(message)
    if key: return i18n.t(key)
    overlay=meta.get(i18n.get_lang(),{})
    return overlay.get("messages",{}).get(message,message) if isinstance(overlay,dict) else message
