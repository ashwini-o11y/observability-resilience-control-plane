import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "experiments" / "exp-001b" / "run-pressure.sh"
ANALYZER = ROOT / "experiments" / "exp-001b" / "analyze-results.py"


def test_exp001b_scripts_exist() -> None:
    assert SCRIPT.exists()
    assert ANALYZER.exists()


def test_exp001b_rejects_unknown_profile() -> None:
    result = subprocess.run(
        ["bash", str(SCRIPT)],
        cwd=ROOT,
        env={"PATH": "/usr/bin:/bin", "PROFILE": "invalid"},
        text=True,
        capture_output=True,
    )
    assert result.returncode == 2
    assert "PROFILE must be sustained, burst, or extended" in result.stderr


def test_exp001b_rejects_rate_above_safety_limit() -> None:
    result = subprocess.run(
        ["bash", str(SCRIPT)],
        cwd=ROOT,
        env={"PATH": "/usr/bin:/bin", "PROFILE": "sustained", "RATE": "10001"},
        text=True,
        capture_output=True,
    )
    assert result.returncode == 2
    assert "exceeds MAX_RATE" in result.stderr


def test_exp001b_report_builds_observation_sections(tmp_path: Path) -> None:
    results = tmp_path / "results"
    results.mkdir()
    payload = {
        "artifact_type": "exp001b_run_result",
        "experiment": "EXP-001B",
        "run_id": "test-run",
        "profile": "sustained",
        "start_timestamp": "2026-09-27T12:00:00Z",
        "end_timestamp": "2026-09-27T12:00:10Z",
        "status": "PASS",
        "phases": [
            {
                "run_id": "test-run-sustained",
                "workload_target_records": 100,
                "workload_acknowledged_records": 100,
                "workload_achieved_rate": 10.0,
                "kafka_consumer_lag_total": 0,
            }
        ],
        "timeseries": [{"phase": "sustained", "system": {"collector_memory_rss_bytes": 100}}],
        "limitations": ["queue unavailable"],
    }
    (results / "test-run.json").write_text(json.dumps(payload), encoding="utf-8")
    report = tmp_path / "report.md"

    subprocess.run(
        ["python3", str(ANALYZER), "report", "--results-dir", str(results), "--output", str(report)],
        cwd=ROOT,
        check=True,
    )

    text = report.read_text(encoding="utf-8")
    assert "## Observations" in text
    assert "## Interpretation" in text
    assert "## Limitations" in text
    assert "queue unavailable" in text
