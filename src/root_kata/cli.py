from __future__ import annotations

import argparse
from .catalog import list_exercises


def _doctor() -> int:
    from .notebook import doctor
    return 0 if doctor() else 1


def _list() -> int:
    for item in list_exercises():
        req = ", ".join(item["requires"]) or "-"
        print(f"{item['id']:<26} {item['kind']:<7} {item['difficulty']:<8} {req:<6} {item['title']}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="root-kata", description="Local ROOT coding challenges"); sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor", help="Check the local runtime"); sub.add_parser("list", help="List available exercises")
    st = sub.add_parser("start", help="Copy the starter into ./kata/<id>/ and print the statement"); st.add_argument("exercise_id")
    ck = sub.add_parser("check", help="Compile/run/test ./kata/<id>/ solution"); ck.add_argument("exercise_id")
    sub.add_parser("progress", help="Show solved exercises and badges"); return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "doctor": raise SystemExit(_doctor())
    if args.command == "list": raise SystemExit(_list())
    from . import notebook as nb
    if args.command == "start": nb.start(args.exercise_id)
    elif args.command == "check": raise SystemExit(0 if nb.check(args.exercise_id).get("passed") else 1)
    elif args.command == "progress": nb.progress()

if __name__ == "__main__": main()
