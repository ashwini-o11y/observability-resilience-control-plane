#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from baseline_lab.exp001a import ResultBuildInput, build_result, load_result_files, render_report

ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_RESULTS_DIR = ROOT_DIR / "experiments" / "exp-001a" / "results"


def _load_json(path: str | None) -> dict | None:
    if not path:
        return None
    file_path = Path(path)
    if not file_path.exists():
        return None
    return json.loads(file_path.read_text(encoding="utf-8"))


def build_command(args: argparse.Namespace) -> int:
    payload = ResultBuildInput(
        experiment=args.experiment,
        run_id=args.run_id,
        rate=args.rate,
        duration_seconds=args.duration_seconds,
        start_timestamp=args.start_timestamp,
        end_timestamp=args.end_timestamp,
        environment=_load_json(args.environment) or {},
        measurement=_load_json(args.measurement),
        before_snapshot=_load_json(args.before_snapshot),
        after_snapshot=_load_json(args.after_snapshot),
        status=args.status,
        error_message=args.error_message,
    )
    result = build_result(payload)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(output_path)
    return 0


def report_command(args: argparse.Namespace) -> int:
    results = load_result_files(Path(args.results_dir))
    report = render_report(results)
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report, encoding="utf-8")
        print(output_path)
    else:
        print(report, end="")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build and summarize EXP-001A result artifacts.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_parser = subparsers.add_parser("build", help="Assemble one structured EXP-001A result JSON.")
    build_parser.add_argument("--experiment", default="EXP-001A")
    build_parser.add_argument("--run-id", required=True)
    build_parser.add_argument("--rate", type=int, required=True)
    build_parser.add_argument("--duration-seconds", type=int, required=True)
    build_parser.add_argument("--start-timestamp", required=True)
    build_parser.add_argument("--end-timestamp", required=True)
    build_parser.add_argument("--environment", required=True)
    build_parser.add_argument("--measurement")
    build_parser.add_argument("--before-snapshot")
    build_parser.add_argument("--after-snapshot")
    build_parser.add_argument("--status", required=True)
    build_parser.add_argument("--error-message")
    build_parser.add_argument("--output", required=True)
    build_parser.set_defaults(func=build_command)

    report_parser = subparsers.add_parser("report", help="Render a Markdown summary from saved EXP-001A results.")
    report_parser.add_argument("--results-dir", default=str(DEFAULT_RESULTS_DIR))
    report_parser.add_argument(
        "--output",
        default=str(DEFAULT_RESULTS_DIR / "latest-report.md"),
        help="Markdown output path. Use an empty string to print to stdout instead.",
    )
    report_parser.set_defaults(func=report_command)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "report" and args.output == "":
        args.output = None
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
