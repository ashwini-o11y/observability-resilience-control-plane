from pathlib import Path

import yaml


def test_compose_includes_required_baseline_services() -> None:
    compose_path = Path("compose.yaml")
    compose = yaml.safe_load(compose_path.read_text(encoding="utf-8"))
    services = compose["services"]

    assert {"kafka", "kafka-init", "otel-collector", "workload"} <= set(services)
    assert services["kafka"]["ports"] == ["9094:9094"]
    assert services["otel-collector"]["ports"] == ["13133:13133", "8888:8888"]
    assert services["workload"]["profiles"] == ["generator"]
    assert {
        "ENABLE_DYNATRACE",
        "DYNATRACE_OTLP_ENDPOINT",
        "DYNATRACE_API_TOKEN",
        "ENABLE_SPLUNK",
        "SPLUNK_HEC_ENDPOINT",
        "SPLUNK_HEC_TOKEN",
        "SPLUNK_HEC_INDEX",
    } <= set(services["otel-collector"]["environment"])
