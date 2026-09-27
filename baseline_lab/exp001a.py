from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

EXPECTED_RATES = (10, 100, 500, 1000)

_METRIC_LINE_RE = re.compile(
    r'^(?P<name>[a-zA-Z_:][a-zA-Z0-9_:]*)(?:\{(?P<labels>[^}]*)\})?\s+(?P<value>[-+0-9.eE]+)$'
)
_LABEL_RE = re.compile(r'([a-zA-Z_][a-zA-Z0-9_]*)="((?:[^"\\]|\\.)*)"')


@dataclass(frozen=True)
class ResultBuildInput:
    experiment: str
    run_id: str
    rate: int
    duration_seconds: int
    start_timestamp: str
    end_timestamp: str
    environment: dict[str, Any]
    measurement: dict[str, Any] | None
    before_snapshot: dict[str, Any] | None
    after_snapshot: dict[str, Any] | None
    status: str
    error_message: str | None = None


def _parse_labels(raw_labels: str | None) -> dict[str, str]:
    if not raw_labels:
        return {}

    labels: dict[str, str] = {}
    for key, value in _LABEL_RE.findall(raw_labels):
        labels[key] = bytes(value, "utf-8").decode("unicode_escape")
    return labels


def parse_prometheus_metrics(text: str) -> dict[tuple[str, frozenset[tuple[str, str]]], float]:
    series: dict[tuple[str, frozenset[tuple[str, str]]], float] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        match = _METRIC_LINE_RE.match(line)
        if not match:
            continue

        labels = frozenset(_parse_labels(match.group("labels")).items())
        series[(match.group("name"), labels)] = float(match.group("value"))
    return series


def _sum_metric(
    series: dict[tuple[str, frozenset[tuple[str, str]]], float],
    metric_name: str,
    **required_labels: str,
) -> float | None:
    total = 0.0
    found = False
    for (name, labels), value in series.items():
        if name != metric_name:
            continue
        label_map = dict(labels)
        if all(label_map.get(key) == expected for key, expected in required_labels.items()):
            total += value
            found = True
    return total if found else None


def _metric_delta(before: float | None, after: float | None) -> float | None:
    if before is None or after is None:
        return None
    return after - before


def _labelled_metric_values(
    series: dict[tuple[str, frozenset[tuple[str, str]]], float],
    metric_name: str,
    label_name: str,
    label_values: tuple[str, ...],
) -> dict[str, float | None]:
    values = {label_value: None for label_value in label_values}
    for label_value in label_values:
        values[label_value] = _sum_metric(series, metric_name, **{label_name: label_value})
    return values


def collect_metric_snapshot(metrics_text: str, *, collected_at: str) -> dict[str, Any]:
    series = parse_prometheus_metrics(metrics_text)
    queue_size = _labelled_metric_values(
        series,
        "otelcol_exporter_queue_size",
        "exporter",
        ("debug", "file"),
    )
    queue_capacity = _labelled_metric_values(
        series,
        "otelcol_exporter_queue_capacity",
        "exporter",
        ("debug", "file"),
    )
    limitations: list[str] = []
    if all(value is None for value in queue_size.values()) and all(
        value is None for value in queue_capacity.values()
    ):
        limitations.append(
            "Collector queue pressure metrics were not exposed by the baseline collector configuration during this scrape."
        )

    return {
        "collected_at": collected_at,
        "otel": {
            "receiver": {
                "accepted_records_total": _sum_metric(
                    series,
                    "otelcol_receiver_accepted_log_records",
                    receiver="kafka",
                )
            },
            "exporter": {
                "sent_records_total": {
                    "debug": _sum_metric(series, "otelcol_exporter_sent_log_records", exporter="debug"),
                    "file": _sum_metric(series, "otelcol_exporter_sent_log_records", exporter="file"),
                },
                "failed_records_total": {
                    "debug": _sum_metric(
                        series,
                        "otelcol_exporter_send_failed_log_records",
                        exporter="debug",
                    ),
                    "file": _sum_metric(
                        series,
                        "otelcol_exporter_send_failed_log_records",
                        exporter="file",
                    ),
                },
            },
            "batch": {
                "send_size_count_total": _sum_metric(
                    series,
                    "otelcol_processor_batch_batch_send_size_count",
                    processor="batch",
                ),
                "send_size_sum_total": _sum_metric(
                    series,
                    "otelcol_processor_batch_batch_send_size_sum",
                    processor="batch",
                ),
                "timeout_trigger_send_total": _sum_metric(
                    series,
                    "otelcol_processor_batch_timeout_trigger_send",
                    processor="batch",
                ),
                "metadata_cardinality": _sum_metric(
                    series,
                    "otelcol_processor_batch_metadata_cardinality",
                    processor="batch",
                ),
            },
            "queue": {
                "size": queue_size,
                "capacity": queue_capacity,
            },
        },
        "system": {
            "collector_cpu_seconds_total": _sum_metric(series, "otelcol_process_cpu_seconds"),
            "collector_memory_rss_bytes": _sum_metric(series, "otelcol_process_memory_rss"),
            "collector_runtime_heap_alloc_bytes": _sum_metric(
                series,
                "otelcol_process_runtime_heap_alloc_bytes",
            ),
            "collector_runtime_total_sys_memory_bytes": _sum_metric(
                series,
                "otelcol_process_runtime_total_sys_memory_bytes",
            ),
            "collector_uptime_seconds": _sum_metric(series, "otelcol_process_uptime"),
        },
        "limitations": limitations,
    }


def build_result(payload: ResultBuildInput) -> dict[str, Any]:
    measurement = payload.measurement or {}
    before_snapshot = payload.before_snapshot or {}
    after_snapshot = payload.after_snapshot or {}

    before_otel = before_snapshot.get("otel", {})
    after_otel = after_snapshot.get("otel", {})
    before_system = before_snapshot.get("system", {})
    after_system = after_snapshot.get("system", {})

    batch_send_size_count_delta = _metric_delta(
        before_otel.get("batch", {}).get("send_size_count_total"),
        after_otel.get("batch", {}).get("send_size_count_total"),
    )
    batch_send_size_sum_delta = _metric_delta(
        before_otel.get("batch", {}).get("send_size_sum_total"),
        after_otel.get("batch", {}).get("send_size_sum_total"),
    )
    timeout_trigger_delta = _metric_delta(
        before_otel.get("batch", {}).get("timeout_trigger_send_total"),
        after_otel.get("batch", {}).get("timeout_trigger_send_total"),
    )
    average_batch_size = None
    if batch_send_size_count_delta not in (None, 0) and batch_send_size_sum_delta is not None:
        average_batch_size = batch_send_size_sum_delta / batch_send_size_count_delta

    limitations: list[str] = []
    for limitation in list(before_snapshot.get("limitations", [])) + list(after_snapshot.get("limitations", [])):
        if limitation not in limitations:
            limitations.append(limitation)
    if measurement.get("accounting_note") and str(measurement["accounting_note"]) not in limitations:
        limitations.append(str(measurement["accounting_note"]))

    return {
        "artifact_type": "exp001a_run_result",
        "experiment": payload.experiment,
        "run_id": payload.run_id,
        "rate": payload.rate,
        "duration_seconds": payload.duration_seconds,
        "start_timestamp": payload.start_timestamp,
        "end_timestamp": payload.end_timestamp,
        "git_commit_sha": payload.environment.get("git_commit_sha"),
        "environment": payload.environment,
        "workload": {
            "target_records": measurement.get("workload_target_records"),
            "acknowledged_records": measurement.get("workload_acknowledged_records"),
            "failed_records": measurement.get("workload_failed_records"),
            "achieved_rate": measurement.get("workload_achieved_rate"),
            "elapsed_seconds": measurement.get("workload_elapsed_seconds"),
        },
        "kafka": {
            "produced_records": measurement.get("kafka_log_end_offset_delta"),
            "consumer_offset_delta": measurement.get("kafka_consumer_current_offset_delta"),
            "consumer_lag": measurement.get("kafka_consumer_lag_total"),
        },
        "otel": {
            "receiver": {
                "accepted_records": measurement.get("otel_receiver_accepted_delta"),
            },
            "exporter": {
                "sent_records": {
                    "debug": measurement.get("otel_exporter_debug_sent_delta"),
                    "file": measurement.get("otel_exporter_file_sent_delta"),
                },
                "failed_records": {
                    "debug": _metric_delta(
                        before_otel.get("exporter", {}).get("failed_records_total", {}).get("debug"),
                        after_otel.get("exporter", {}).get("failed_records_total", {}).get("debug"),
                    ),
                    "file": _metric_delta(
                        before_otel.get("exporter", {}).get("failed_records_total", {}).get("file"),
                        after_otel.get("exporter", {}).get("failed_records_total", {}).get("file"),
                    ),
                },
            },
            "queue": after_otel.get("queue"),
            "batch": {
                "timeout_trigger_send_delta": timeout_trigger_delta,
                "send_size_count_delta": batch_send_size_count_delta,
                "send_size_sum_delta": batch_send_size_sum_delta,
                "average_batch_size": average_batch_size,
                "metadata_cardinality": after_otel.get("batch", {}).get("metadata_cardinality"),
            },
        },
        "system": {
            "collector_cpu_seconds_delta": _metric_delta(
                before_system.get("collector_cpu_seconds_total"),
                after_system.get("collector_cpu_seconds_total"),
            ),
            "collector_memory_rss_bytes": after_system.get("collector_memory_rss_bytes"),
            "collector_runtime_heap_alloc_bytes": after_system.get("collector_runtime_heap_alloc_bytes"),
            "collector_runtime_total_sys_memory_bytes": after_system.get(
                "collector_runtime_total_sys_memory_bytes"
            ),
            "collector_uptime_seconds": after_system.get("collector_uptime_seconds"),
        },
        "status": payload.status,
        "error_message": payload.error_message,
        "limitations": limitations,
    }


def load_result_files(results_dir: Path) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for path in sorted(results_dir.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if payload.get("artifact_type") != "exp001a_run_result":
            continue
        if payload.get("experiment") != "EXP-001A" or "run_id" not in payload:
            continue
        payload["_path"] = str(path)
        results.append(payload)
    return results


def _safe_ratio(numerator: float | int | None, denominator: float | int | None) -> float | None:
    if numerator is None or denominator in (None, 0):
        return None
    return float(numerator) / float(denominator)


def _format_number(value: float | int | None, decimals: int = 2) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, int) or (isinstance(value, float) and value.is_integer()):
        return str(int(value))
    return f"{value:.{decimals}f}"


def _rate_summary_row(result: dict[str, Any] | None) -> str:
    if result is None:
        return "| missing | missing | missing | missing | missing | missing | missing | missing |"

    workload = result.get("workload", {})
    kafka = result.get("kafka", {})
    otel = result.get("otel", {})
    system = result.get("system", {})
    exporter_sent = otel.get("exporter", {}).get("sent_records", {})
    exporter_failed = otel.get("exporter", {}).get("failed_records", {})
    throughput_ratio = _safe_ratio(workload.get("achieved_rate"), result.get("rate"))
    receiver_loss = None
    if workload.get("acknowledged_records") is not None and otel.get("receiver", {}).get("accepted_records") is not None:
        receiver_loss = workload["acknowledged_records"] - otel["receiver"]["accepted_records"]

    return (
        f"| {result.get('run_id', 'missing')} | {result.get('status', 'n/a')} | "
        f"{_format_number(workload.get('acknowledged_records'))}/{_format_number(workload.get('target_records'))} | "
        f"{_format_number(workload.get('achieved_rate'))} ({_format_number(throughput_ratio * 100 if throughput_ratio is not None else None)}%) | "
        f"{_format_number(kafka.get('consumer_lag'))} | "
        f"{_format_number(receiver_loss)} | "
        f"{_format_number((exporter_failed.get('debug') or 0) + (exporter_failed.get('file') or 0))} | "
        f"{_format_number(system.get('collector_memory_rss_bytes') / (1024 * 1024) if system.get('collector_memory_rss_bytes') is not None else None)} MiB |"
    )


def render_report(results: list[dict[str, Any]]) -> str:
    def sort_key(item: dict[str, Any]) -> tuple[int, float, str, str]:
        run_id = str(item.get("run_id", ""))
        start_timestamp = item.get("start_timestamp")
        if isinstance(start_timestamp, str):
            normalized = start_timestamp.replace("Z", "+00:00")
            try:
                return (
                    1,
                    datetime.fromisoformat(normalized).timestamp(),
                    run_id,
                    str(item.get("_path", "")),
                )
            except ValueError:
                pass
        return (0, 0.0, run_id, str(item.get("_path", "")))

    latest_by_rate: dict[int, dict[str, Any]] = {}
    for result in sorted(results, key=sort_key):
        rate = result.get("rate")
        if isinstance(rate, int):
            latest_by_rate[rate] = result

    lines = [
        "# EXP-001A Normal-Load Baseline Summary",
        "",
        "This report summarizes **observed behaviour in this repository's current baseline environment only**. It is not a universal Kafka or OpenTelemetry performance limit.",
        "",
        f"Generated from {len(results)} run result(s).",
        "",
        "## Rate comparison",
        "",
        "| Requested rate | Run ID | Status | Acked/Target | Achieved rate | Kafka lag | Receiver loss | Export failures | Collector RSS |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]

    for rate in EXPECTED_RATES:
        lines.append(f"| {rate}/s {_rate_summary_row(latest_by_rate.get(rate))}")

    available_results = [latest_by_rate[rate] for rate in EXPECTED_RATES if rate in latest_by_rate]
    lines.extend(
        [
            "",
            "## Observed environment behaviour",
            "",
        ]
    )
    if not available_results:
        lines.append("- No EXP-001A run results were available.")
    else:
        for result in available_results:
            workload = result.get("workload", {})
            kafka = result.get("kafka", {})
            otel = result.get("otel", {})
            system = result.get("system", {})
            rate = result.get("rate")
            receiver = otel.get("receiver", {}).get("accepted_records")
            acknowledged = workload.get("acknowledged_records")
            debug_failed = otel.get("exporter", {}).get("failed_records", {}).get("debug")
            file_failed = otel.get("exporter", {}).get("failed_records", {}).get("file")
            lines.append(
                "- "
                f"{rate}/s run `{result.get('run_id')}` ended with status `{result.get('status')}`; "
                f"workload acknowledged {_format_number(acknowledged)} of {_format_number(workload.get('target_records'))} target records, "
                f"Kafka lag finished at {_format_number(kafka.get('consumer_lag'))}, "
                f"collector receiver accepted {_format_number(receiver)} records, "
                f"exporter failures were debug={_format_number(debug_failed)} file={_format_number(file_failed)}, "
                f"collector RSS ended at {_format_number(system.get('collector_memory_rss_bytes') / (1024 * 1024) if system.get('collector_memory_rss_bytes') is not None else None)} MiB."
            )
        degradation_candidates = [
            result
            for result in available_results
            if (
                result.get("kafka", {}).get("consumer_lag", 0) not in (None, 0)
                or result.get("otel", {}).get("exporter", {}).get("failed_records", {}).get("debug", 0) not in (None, 0)
                or result.get("otel", {}).get("exporter", {}).get("failed_records", {}).get("file", 0) not in (None, 0)
            )
        ]
        if degradation_candidates:
            first_rate = min(result["rate"] for result in degradation_candidates if isinstance(result.get("rate"), int))
            lines.append(
                f"- First visible degradation in the available results appears at {first_rate}/s or above, based on non-zero lag or exporter failures in this environment."
            )
        else:
            lines.append(
                "- No non-zero Kafka lag or exporter failure counters were observed in the currently available result set."
            )

    lines.extend(
        [
            "",
            "## General Kafka/OTel context",
            "",
            "- Kafka offsets, collector counters, and process metrics in these results are environment-specific measurements from this baseline stack.",
            "- Queue pressure fields remain `null` when the pinned collector configuration does not expose queue metrics for the enabled exporters.",
            "- Treat these results as a reproducible local baseline for later experiments, not as a universal system capacity claim.",
        ]
    )

    return "\n".join(lines) + "\n"
