from __future__ import annotations

import argparse
from . import i18n
from .catalog import difficulty_label, list_exercises, localized


def _doctor() -> int:
    from .notebook import doctor
    return 0 if doctor() else 1


def _list() -> int:
    for item in list_exercises():
        view = localized(item)
        req = ", ".join(item["requires"]) or "-"
        print(f"{item['id']:<26} {item['kind']:<7} {difficulty_label(view['difficulty']):<8} {req:<6} {view['title']}")
    return 0


def _config(lang: str | None) -> int:
    if lang is None:
        print(i18n.t("config_current", lang=i18n.get_lang()))
        return 0
    try:
        chosen = i18n.set_lang(lang)
    except ValueError as exc:
        print(exc)
        return 1
    print(i18n.t("config_set", lang=chosen))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="root-kata", description="Local ROOT coding challenges"); sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor", help="Check the local runtime"); sub.add_parser("list", help="List available exercises")
    st = sub.add_parser("start", help="Copy the starter into ./kata/<id>/ and print the statement"); st.add_argument("exercise_id")
    ck = sub.add_parser("check", help="Compile/run/test ./kata/<id>/ solution"); ck.add_argument("exercise_id")
    sub.add_parser("progress", help="Show solved exercises and badges")
    lb = sub.add_parser("lab", help="Start JupyterLab for ROOT Kata (http://127.0.0.1:8888)"); lb.add_argument("--port", type=int, default=8888)
    cf = sub.add_parser("config", help="Show or set the interface language (es/en)"); cf.add_argument("--lang", choices=["es", "en"]); return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "doctor": raise SystemExit(_doctor())
    if args.command == "list": raise SystemExit(_list())
    if args.command == "config": raise SystemExit(_config(args.lang))
    if args.command == "lab":
        from .lab import lab
        raise SystemExit(lab(port=args.port))
    from . import notebook as nb
    if args.command == "start": nb.start(args.exercise_id)
    elif args.command == "check": raise SystemExit(0 if nb.check(args.exercise_id).get("passed") else 1)
    elif args.command == "progress": nb.progress()

if __name__ == "__main__": main()
