from __future__ import annotations
import json, os
from pathlib import Path
from typing import Any
from . import i18n

REQUIRED_FIELDS={"id","title","track","difficulty","summary","description","requirements","entrypoint","starter","validator","requires"}
LOCALIZED_FIELDS=("title","track","difficulty","summary","description","requirements","hints","topics","examples","learning_goal","preview")
_DEFAULT_MESSAGE_KEYS={"Values differ":"val.values_differ","Values are not close":"val.not_close","Passed":"val.case_passed"}

# Frozen MVP path. New curriculum may extend beyond it, but this initial route and
# its completion semantics stay stable as the catalog grows.
STARTER_PATH_IDS=(
    "cpp-hello-world",
    "cpp-array-index",
    "cpp-array-print",
    "cpp-sum-positive",
    "cpp-count-above",
    "cpp-root-histogram",
)

TRANSFER_LEVELS=("introductory","basic","applied","transfer","challenge")
_CURRICULUM_FIELDS={"competency","prerequisites","transfer_level","misconception","observable_success","source"}
_SOURCE_FIELDS={"repository","path","concept"}


def repository_root()->Path:return Path(__file__).resolve().parents[2]
def exercises_root()->Path:
    override=os.environ.get("ROOT_KATA_EXERCISES")
    return Path(override).expanduser().resolve() if override else Path(__file__).resolve().parent/"exercises"


def validate_curriculum(data:dict[str,Any],*,label:str="exercise")->None:
    """Validate the durable authoring contract used by autonomous additions.

    The six original starter katas predate this contract and are intentionally
    grandfathered. Every later exercise must carry explicit curriculum metadata.
    """
    curriculum=data.get("curriculum")
    if curriculum is None and data.get("id") in STARTER_PATH_IDS:
        return
    if not isinstance(curriculum,dict):
        raise ValueError(f"{label}: new exercises need a 'curriculum' object")
    missing=sorted(_CURRICULUM_FIELDS-curriculum.keys())
    if missing:
        raise ValueError(f"{label}: curriculum missing fields: {', '.join(missing)}")
    level=str(curriculum.get("transfer_level","")).lower()
    if level not in TRANSFER_LEVELS:
        raise ValueError(f"{label}: curriculum.transfer_level must be one of {', '.join(TRANSFER_LEVELS)}")
    for field in ("competency","misconception","observable_success"):
        if not isinstance(curriculum.get(field),str) or not curriculum[field].strip():
            raise ValueError(f"{label}: curriculum.{field} must be a non-empty string")
    prerequisites=curriculum.get("prerequisites")
    if not isinstance(prerequisites,list) or any(not isinstance(x,str) or not x.strip() for x in prerequisites):
        raise ValueError(f"{label}: curriculum.prerequisites must be a list of exercise ids")
    if len(prerequisites)!=len(set(prerequisites)):
        raise ValueError(f"{label}: curriculum.prerequisites contains duplicates")
    if data.get("id") in prerequisites:
        raise ValueError(f"{label}: an exercise cannot require itself")
    source=curriculum.get("source")
    if not isinstance(source,dict):
        raise ValueError(f"{label}: curriculum.source must be an object")
    source_missing=sorted(_SOURCE_FIELDS-source.keys())
    if source_missing:
        raise ValueError(f"{label}: curriculum.source missing fields: {', '.join(source_missing)}")
    for field in _SOURCE_FIELDS:
        if not isinstance(source.get(field),str) or not source[field].strip():
            raise ValueError(f"{label}: curriculum.source.{field} must be a non-empty string")


def _load_metadata(path:Path)->dict[str,Any]:
    data=json.loads(path.read_text(encoding="utf-8")); missing=sorted(REQUIRED_FIELDS-data.keys())
    if missing: raise ValueError(f"{path}: missing fields: {', '.join(missing)}")
    if data["id"]!=path.parent.name: raise ValueError(f"{path}: id must match directory name")
    data.setdefault("kind","python")
    if data["kind"] not in ("python","cpp"): raise ValueError(f"{path}: kind must be 'python' or 'cpp'")
    if data["kind"]=="cpp" and "harness" not in data: raise ValueError(f"{path}: cpp exercises need a 'harness' file")
    validate_curriculum(data,label=str(path))
    return data


def list_exercises(*,include_unpublished:bool=False)->list[dict[str,Any]]:
    loaded=[]
    for metadata_path in sorted(exercises_root().glob("*/exercise.json")):
        loaded.append(_load_metadata(metadata_path))
    known_ids={data["id"] for data in loaded}
    for data in loaded:
        curriculum=data.get("curriculum") or {}
        for prerequisite in curriculum.get("prerequisites",[]):
            if prerequisite not in known_ids:
                raise ValueError(f"{data['id']}: unknown curriculum prerequisite {prerequisite!r}")
    items=[]
    for data in loaded:
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
def case_label(meta:dict[str,Any],name:str,*,lang:str|None=None)->str:
    overlay=meta.get(i18n.normalize(lang) or i18n.get_lang(),{})
    return overlay.get("cases",{}).get(name,name) if isinstance(overlay,dict) else name
def message_label(meta:dict[str,Any],message:str|None,*,lang:str|None=None)->str|None:
    if message is None: return None
    key=_DEFAULT_MESSAGE_KEYS.get(message)
    language=i18n.normalize(lang) or i18n.get_lang()
    if key: return i18n.translate(key,language)
    overlay=meta.get(language,{})
    return overlay.get("messages",{}).get(message,message) if isinstance(overlay,dict) else message
