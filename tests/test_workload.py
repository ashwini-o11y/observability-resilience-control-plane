import pytest

from opentelemetry.proto.collector.logs.v1.logs_service_pb2 import ExportLogsServiceRequest

from baseline_lab.workload import WorkloadConfig, build_log_request, build_rate_schedule


def test_build_rate_schedule_with_ramp_up() -> None:
    schedule = build_rate_schedule(rate=1000, duration_seconds=5, ramp_up_seconds=2)

    assert schedule == [
        500,
        1000,
        1000,
        1000,
        1000,
    ]
    assert sum(schedule) == 4500


def test_build_rate_schedule_rounds_up_low_rate_ramp() -> None:
    schedule = build_rate_schedule(rate=3, duration_seconds=4, ramp_up_seconds=2)

    assert schedule == [2, 3, 3, 3]
    assert sum(schedule) == 11


def test_workload_config_rejects_invalid_ramp_up() -> None:
    config = WorkloadConfig(rate=100, duration_seconds=10, ramp_up_seconds=10)

    with pytest.raises(ValueError, match="ramp_up_seconds"):
        config.validate()


@pytest.mark.parametrize(
    ("rate", "duration_seconds", "ramp_up_seconds", "expected_message"),
    [
        (0, 10, 0, "rate"),
        (10, 0, 0, "duration_seconds"),
        (10, 10, -1, "ramp_up_seconds"),
        (10, 10, 10, "ramp_up_seconds"),
    ],
)
def test_build_rate_schedule_rejects_invalid_arguments(
    rate: int,
    duration_seconds: int,
    ramp_up_seconds: int,
    expected_message: str,
) -> None:
    with pytest.raises(ValueError, match=expected_message):
        build_rate_schedule(
            rate=rate,
            duration_seconds=duration_seconds,
            ramp_up_seconds=ramp_up_seconds,
        )


def test_build_log_request_contains_required_schema_fields() -> None:
    request = build_log_request(
        config=WorkloadConfig(
            topic="orion.baseline.telemetry.logs.v1",
            service_name="demo-service",
            service_version="1.2.3",
            environment="local",
        ),
        sequence_number=7,
        run_id="run-001",
        emitted_at_ns=1_725_000_000_000_000_000,
        current_rate=1000,
    )

    decoded = ExportLogsServiceRequest()
    decoded.ParseFromString(request.SerializeToString())

    resource_logs = decoded.resource_logs[0]
    resource_attributes = {item.key: item.value.string_value for item in resource_logs.resource.attributes}
    log_record = resource_logs.scope_logs[0].log_records[0]
    log_attributes = {}
    for item in log_record.attributes:
        value = item.value
        if value.HasField("string_value"):
            log_attributes[item.key] = value.string_value
        elif value.HasField("int_value"):
            log_attributes[item.key] = value.int_value
        elif value.HasField("bool_value"):
            log_attributes[item.key] = value.bool_value

    assert resource_attributes == {
        "service.name": "demo-service",
        "service.version": "1.2.3",
        "deployment.environment": "local",
        "orion.topic": "orion.baseline.telemetry.logs.v1",
    }
    assert log_record.severity_text == "ERROR"
    assert log_attributes["event.type"] == "baseline.payment"
    assert log_attributes["event.sequence"] == 7
    assert log_attributes["event.target_rate"] == 1000
    assert log_attributes["orion.transaction_id"] == "run-001-00000007"
    assert log_attributes["orion.business_criticality"] == "high"
    assert log_attributes["orion.synthetic"] is True
