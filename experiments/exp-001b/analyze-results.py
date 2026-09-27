#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_measurements(directory: Path) -> list[dict[str, Any]]:
    values = []
    for path in sorted(directory.glob("*.measurement.json")):
        payload = load_json(path)
        values.append(payload)
    return values


def load_timeseries(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    values = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            values.append(json.loads(line))
    return values


def build(args: argparse.Namespace) -> None:
    results_dir = Path(args.results_dir)
    results_dir.mkdir(parents=True, exist_ok=True)
    measurements = load_measurements(Path(args.measurement_dir))
    timeseries = load_timeseries(Path(args.timeseries))

    limitations = []
    for sample in timeseries:
        for item in sample.get("limitations", []):
            if item not in limitations:
                limitations.append(item)

    result = {
        "artifact_type": "exp001b_run_result",
        "experiment": args.experiment,
        "run_id": args.run_id,
        "profile": args.profile,
        "start_timestamp": args.start_timestamp,
        "end_timestamp": args.end_timestamp,
        "status": args.status,
        "error_message": args.error_message or None,
        "phases": measurements,
        "timeseries": timeseries,
        "observations": {
            "phase_count": len(measurements),
            "sample_count": len(timeseries),
        },
        "interpretation": {
            "pressure_signal": "Resource or lag growth must be established from observed measurements; no capacity threshold is inferred automatically."
        },
        "limitations": limitations,
    }
    output = Path(args.output)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def render_report(results: list[dict[str, Any]]) -> str:
    lines = [
        "# EXP-001B Telemetry Pressure Characterization",
        "",
        "This report documents observations from the configured pressure experiments in the current local environment. It does not establish a universal Kafka, OpenTelemetry Collector, or exporter capacity limit.",
        "",
        f"Runs available: **{len(results)}**",
        "",
        "## Run summary",
        "",
        "| Run ID | Profile | Status | Phases | Samples |",
        "| --- | --- | --- | ---: | ---: |",
    ]
    for result in results:
        lines.append(
            f"| {result.get('run_id')} | {result.get('profile')} | {result.get('status')} | "
            f"{len(result.get('phases', []))} | {len(result.get('timeseries', []))} |"
        )

    lines += ["", "## Observations", ""]
    if not results:
        lines.append("- No EXP-001B results are available yet.")
    else:
        for result in results:
            for phase in result.get("phases", []):
                lines.append(
                    f"- `{phase.get('run_id', 'unknown')}`: target={fmt(phase.get('workload_target_records'))}, "
                    f"acknowledged={fmt(phase.get('workload_acknowledged_records'))}, "
                    f"achieved_rate={fmt(phase.get('workload_achieved_rate'))}/s, "
                    f"Kafka lag={fmt(phase.get('kafka_consumer_lag_total'))}."
                )

    lines += [
        "",
        "## Interpretation",
        "",
        "- A pressure signal is an observed change in resource use, lag, throughput, or accounting; it is not automatically a failure threshold.",
        "- ORION control behaviour is intentionally out of scope for EXP-001B.",
        "",
        "## Limitations",
        "",
    ]
    limitations = []
    for result in results:
        for item in result.get("limitations", []):
            if item not in limitations:
                limitations.append(item)
    if limitations:
        lines.extend(f"- {item}" for item in limitations)
    else:
        lines.append("- Metrics not exposed by the collector remain unavailable rather than being treated as zero.")

    lines += [
        "",
        "## Next decision",
        "",
        "Use the measured pressure/degradation signals to define the first ORION detection model only after the experiment data is reviewed.",
        "",
    ]
    return "\n".join(lines)


def report(args: argparse.Namespace) -> None:
    results_dir = Path(args.results_dir)
    results = []
    for path in sorted(results_dir.glob("*.json")):
        try:
            payload = load_json(path)
        except json.JSONDecodeError:
            continue
        if payload.get("artifact_type") == "exp001b_run_result":
            results.append(payload)
    Path(args.output).write_text(render_report(results), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    build_parser = sub.add_parser("build")
    build_parser.add_argument("--experiment", required=True)
    build_parser.add_argument("--run-id", required=True)
    build_parser.add_argument("--profile", required=True)
    build_parser.add_argument("--start-timestamp", required=True)
    build_parser.add_argument("--end-timestamp", required=True)
    build_parser.add_argument("--status", required=True)
    build_parser.add_argument("--error-message", default="")
    build_parser.add_argument("--results-dir", required=True)
    build_parser.add_argument("--timeseries", required=True)
    build_parser.add_argument("--measurement-dir", required=True)
    build_parser.add_argument("--output", required=True)
    build_parser.set_defaults(func=build)

    report_parser = sub.add_parser("report")
    report_parser.add_argument("--results-dir", required=True)
    report_parser.add_argument("--output", required=True)
    report_parser.set_defaults(func=report)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
