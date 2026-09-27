import json
from pathlib import Path

from baseline_lab.cli import build_parser

from baseline_lab.exp001a import ResultBuildInput, build_result, collect_metric_snapshot, load_result_files, render_report


def test_workload_cli_accepts_operator_run_id() -> None:
    args = build_parser().parse_args(["--run-id", "exp001a-100rps-001"])

    assert args.run_id == "exp001a-100rps-001"


def test_collect_metric_snapshot_extracts_known_metrics_and_limitations() -> None:
    snapshot = collect_metric_snapshot(
        """
        # HELP otelcol_exporter_send_failed_log_records Number of log records in failed attempts to send to destination.
        otelcol_exporter_send_failed_log_records{exporter="debug"} 0
        otelcol_exporter_send_failed_log_records{exporter="file"} 0
        otelcol_exporter_sent_log_records{exporter="debug"} 30
        otelcol_exporter_sent_log_records{exporter="file"} 30
        otelcol_process_cpu_seconds{} 0.24
        otelcol_process_memory_rss{} 172011520
        otelcol_process_runtime_total_sys_memory_bytes{} 65164552
        otelcol_processor_batch_batch_send_size_count{processor="batch"} 3
        otelcol_processor_batch_batch_send_size_sum{processor="batch"} 30
        otelcol_processor_batch_metadata_cardinality{processor="batch"} 1
        otelcol_processor_batch_timeout_trigger_send{processor="batch"} 3
        otelcol_receiver_accepted_log_records{receiver="kafka"} 30
        """,
        collected_at="2026-09-27T11:00:00Z",
    )

    assert snapshot["otel"]["receiver"]["accepted_records_total"] == 30
    assert snapshot["otel"]["exporter"]["sent_records_total"] == {"debug": 30, "file": 30}
    assert snapshot["system"]["collector_cpu_seconds_total"] == 0.24
    assert snapshot["otel"]["queue"] == {"size": None, "capacity": None}
    assert snapshot["limitations"] == [
        "Collector queue pressure metrics were not exposed by the baseline collector configuration during this scrape."
    ]


def test_build_result_and_render_report_use_available_rates_only() -> None:
    measurement = {
        "accounting_note": "window deltas only",
        "kafka_consumer_current_offset_delta": 10,
        "kafka_consumer_lag_total": 0,
        "kafka_log_end_offset_delta": 10,
        "otel_exporter_debug_sent_delta": 10,
        "otel_exporter_file_sent_delta": 10,
        "otel_receiver_accepted_delta": 10,
        "workload_achieved_rate": 9.9,
        "workload_acknowledged_records": 10,
        "workload_elapsed_seconds": 1.01,
        "workload_failed_records": 0,
        "workload_target_records": 10,
    }
    before_snapshot = {
        "otel": {
            "batch": {
                "metadata_cardinality": 1,
                "send_size_count_total": 1,
                "send_size_sum_total": 10,
                "timeout_trigger_send_total": 1,
            },
            "exporter": {"failed_records_total": {"debug": 0, "file": 0}},
            "queue": {"size": None, "capacity": None},
        },
        "system": {"collector_cpu_seconds_total": 1.0},
        "limitations": ["queue unavailable"],
    }
    after_snapshot = {
        "otel": {
            "batch": {
                "metadata_cardinality": 1,
                "send_size_count_total": 2,
                "send_size_sum_total": 20,
                "timeout_trigger_send_total": 2,
            },
            "exporter": {"failed_records_total": {"debug": 0, "file": 0}},
            "queue": {"size": None, "capacity": None},
        },
        "system": {
            "collector_cpu_seconds_total": 1.5,
            "collector_memory_rss_bytes": 200_000_000,
            "collector_runtime_heap_alloc_bytes": 10_000_000,
            "collector_runtime_total_sys_memory_bytes": 60_000_000,
            "collector_uptime_seconds": 100.0,
        },
        "limitations": ["queue unavailable"],
    }
    result = build_result(
        ResultBuildInput(
            experiment="EXP-001A",
            run_id="exp001a-10rps-001",
            rate=10,
            duration_seconds=1,
            start_timestamp="2026-09-27T11:00:00Z",
            end_timestamp="2026-09-27T11:00:01Z",
            environment={"git_commit_sha": "abc123"},
            measurement=measurement,
            before_snapshot=before_snapshot,
            after_snapshot=after_snapshot,
            status="PASS",
        )
    )

    assert result["otel"]["batch"]["average_batch_size"] == 10
    assert result["system"]["collector_cpu_seconds_delta"] == 0.5
    assert result["limitations"] == ["queue unavailable", "window deltas only"]

    report = render_report([result])

    assert "| 10/s | exp001a-10rps-001 | PASS |" in report
    assert "| 100/s | missing |" in report
    assert "Observed environment behaviour" in report
    assert "not as a universal system capacity claim" in report


def test_load_result_files_only_reads_results_directory_json(tmp_path) -> None:
    results_dir = tmp_path / "results"
    results_dir.mkdir()
    (results_dir / "exp001a-10rps-001.json").write_text(
        json.dumps({"experiment": "EXP-001A", "run_id": "exp001a-10rps-001"}),
        encoding="utf-8",
    )
    (tmp_path / "result-schema.json").write_text(
        json.dumps({"experiment": "EXP-001A", "run_id": "schema"}),
        encoding="utf-8",
    )

    results = load_result_files(Path(results_dir))

    assert [result["run_id"] for result in results] == ["exp001a-10rps-001"]
