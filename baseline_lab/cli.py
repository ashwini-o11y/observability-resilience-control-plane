from __future__ import annotations

import argparse

from baseline_lab.constants import (
    TOPIC_NAME,
    WORKLOAD_ENVIRONMENT,
    WORKLOAD_SERVICE_NAME,
    WORKLOAD_SERVICE_VERSION,
)
from baseline_lab.workload import WorkloadConfig, run_workload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate deterministic OTLP log traffic for the ORION baseline lab."
    )
    parser.add_argument("--bootstrap-servers", default="kafka:9092")
    parser.add_argument("--topic", default=TOPIC_NAME)
    parser.add_argument("--rate", type=int, default=100, help="Steady-state peak events per second target.")
    parser.add_argument("--duration", dest="duration_seconds", type=int, default=30)
    parser.add_argument(
        "--ramp-up-seconds",
        type=int,
        default=0,
        help="Seconds spent linearly ramping toward --rate without compensating later overshoot.",
    )
    parser.add_argument("--service-name", default=WORKLOAD_SERVICE_NAME)
    parser.add_argument("--service-version", default=WORKLOAD_SERVICE_VERSION)
    parser.add_argument("--environment", default=WORKLOAD_ENVIRONMENT)
    parser.add_argument("--metrics-port", type=int, default=9102)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    config = WorkloadConfig(
        bootstrap_servers=args.bootstrap_servers,
        topic=args.topic,
        rate=args.rate,
        duration_seconds=args.duration_seconds,
        ramp_up_seconds=args.ramp_up_seconds,
        service_name=args.service_name,
        service_version=args.service_version,
        environment=args.environment,
        metrics_port=args.metrics_port,
    )
    summary = run_workload(config)
    print(summary.to_json())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
