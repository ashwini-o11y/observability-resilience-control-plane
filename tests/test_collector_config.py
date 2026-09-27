import yaml
from pathlib import Path

from baseline_lab.render_collector_config import build_config_text


def test_baseline_collector_config_uses_debug_and_file_exporters_only() -> None:
    config = yaml.safe_load(build_config_text(enable_dynatrace=False, enable_splunk=False))

    assert config["receivers"]["kafka"]["topic"] == "orion.baseline.telemetry.logs.v1"
    assert config["receivers"]["kafka"]["group_id"] == "orion-baseline-collector"
    assert config["processors"]["memory_limiter"]["limit_mib"] == 256
    assert config["processors"]["batch"]["send_batch_size"] == 1024
    assert config["service"]["pipelines"]["logs"]["exporters"] == ["debug", "file"]


def test_optional_exporters_are_added_without_inlining_secrets() -> None:
    config_text = build_config_text(enable_dynatrace=True, enable_splunk=True)
    config = yaml.safe_load(config_text)

    assert "otlphttp/dynatrace" in config["exporters"]
    assert "splunk_hec" in config["exporters"]
    assert "${env:DYNATRACE_API_TOKEN}" in config_text
    assert "${env:SPLUNK_HEC_TOKEN}" in config_text
    assert config["service"]["pipelines"]["logs"]["exporters"] == [
        "debug",
        "file",
        "otlphttp/dynatrace",
        "splunk_hec",
    ]


def test_committed_generated_collector_config_matches_renderer() -> None:
    generated_path = Path("collector/collector.generated.yaml")

    assert generated_path.read_text(encoding="utf-8") == build_config_text(
        enable_dynatrace=False,
        enable_splunk=False,
    )
