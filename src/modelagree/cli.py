import argparse
import json
import sys

from .report import report
from .runner import run
from .scoring import score


def main(argv=None):
    parser = argparse.ArgumentParser(prog="modelagree", description="Audit model label agreement")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("run", help="Run or resume a frozen config").add_argument("config")
    commands.add_parser("score", help="Write scores.json").add_argument("run_dir")
    commands.add_parser("report", help="Write a self-contained HTML report").add_argument("run_dir")
    args = parser.parse_args(argv)
    try:
        if args.command == "run":
            print(run(args.config))
        elif args.command == "score":
            print(json.dumps(score(args.run_dir), indent=2, ensure_ascii=False))
        else:
            print(report(args.run_dir))
    except (ValueError, OSError, KeyError) as exc:
        print(f"modelagree: {exc}", file=sys.stderr)
        return 1
    return 0
