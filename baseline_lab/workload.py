from __future__ import annotations

import json
import logging
import math
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Iterable

from confluent_kafka import Producer
from prometheus_client import Counter, Gauge, start_http_server

from opentelemetry.proto.collector.logs.v1.logs_service_pb2 import ExportLogsServiceRequest
from opentelemetry.proto.common.v1.common_pb2 import AnyValue, InstrumentationScope, KeyValue
from opentelemetry.proto.logs.v1.logs_pb2 import LogRecord, ResourceLogs, ScopeLogs, SeverityNumber
from opentelemetry.proto.resource.v1.resource_pb2 import Resource

from baseline_lab import __version__
from baseline_lab.constants import (
    TOPIC_NAME,
    WORKLOAD_ENVIRONMENT,
    WORKLOAD_SERVICE_NAME,
    WORKLOAD_SERVICE_VERSION,
)

LOGGER = logging.getLogger(__name__)

EVENTS_SENT = Counter(
    "orion_workload_events_sent_total",
    "Number of OTLP log envelopes acknowledged by Kafka.",
)
EVENTS_FAILED = Counter(
    "orion_workload_events_failed_total",
    "Number of workload events that failed to publish to Kafka.",
)
LAST_RUN_ACKNOWLEDGED = Gauge(
    "orion_workload_last_run_acknowledged_events",
    "Number of events acknowledged during the most recent workload run.",
)
LAST_RUN_FAILED = Gauge(
    "orion_workload_last_run_failed_events",
    "Number of events that failed during the most recent workload run.",
)
TARGET_RATE = Gauge(
    "orion_workload_target_rate_events_per_second",
    "Configured event rate for the current second.",
)
ACTUAL_RATE = Gauge(
    "orion_workload_actual_rate_events_per_second",
    "Achieved event rate for the previous second window.",
)
LAST_RUN_DURATION = Gauge(
    "orion_workload_last_run_duration_seconds",
    "Observed duration of the most recent workload execution.",
)

SEVERITIES: tuple[tuple[str, int], ...] = (
    ("INFO", SeverityNumber.SEVERITY_NUMBER_INFO),
    ("WARN", SeverityNumber.SEVERITY_NUMBER_WARN),
    ("ERROR", SeverityNumber.SEVERITY_NUMBER_ERROR),
    ("DEBUG", SeverityNumber.SEVERITY_NUMBER_DEBUG),
)
EVENT_TYPES: tuple[str, ...] = (
    "baseline.checkout",
    "baseline.inventory",
    "baseline.payment",
    "baseline.fulfillment",
)
BUSINESS_CRITICALITIES: tuple[str, ...] = ("low", "medium", "high", "critical")


@dataclass(frozen=True)
class WorkloadConfig:
    bootstrap_servers: str = "kafka:9092"
    topic: str = TOPIC_NAME
    rate: int = 100
    duration_seconds: int = 30
    ramp_up_seconds: int = 0
    run_id: str | None = None
    service_name: str = WORKLOAD_SERVICE_NAME
    service_version: str = WORKLOAD_SERVICE_VERSION
    environment: str = WORKLOAD_ENVIRONMENT
    metrics_port: int | None = None
    compression_type: str = "gzip"
    acks: str = "all"
    linger_ms: int = 5
    batch_size: int = 65536
    request_timeout_ms: int = 10000

    def validate(self) -> None:
        if self.rate <= 0:
            raise ValueError("rate must be greater than zero")
        if self.duration_seconds <= 0:
            raise ValueError("duration_seconds must be greater than zero")
        if self.ramp_up_seconds < 0:
            raise ValueError("ramp_up_seconds must be zero or greater")
        if self.ramp_up_seconds >= self.duration_seconds:
            raise ValueError("ramp_up_seconds must be less than duration_seconds")
        if not self.bootstrap_servers.strip():
            raise ValueError("bootstrap_servers must not be empty")
        if not self.topic.strip():
            raise ValueError("topic must not be empty")
        if self.run_id is not None and not self.run_id.strip():
            raise ValueError("run_id must not be empty when provided")


@dataclass(frozen=True)
class WorkloadSummary:
    run_id: str
    target_events: int
    acknowledged_events: int
    failed_events: int
    elapsed_seconds: float

    @property
    def achieved_rate(self) -> float:
        if self.elapsed_seconds <= 0:
            return 0.0
        return self.acknowledged_events / self.elapsed_seconds

    def to_json(self) -> str:
        return json.dumps(
            {
                "run_id": self.run_id,
                "target_events": self.target_events,
                "acknowledged_events": self.acknowledged_events,
                "failed_events": self.failed_events,
                "elapsed_seconds": round(self.elapsed_seconds, 3),
                "achieved_rate": round(self.achieved_rate, 3),
            },
            sort_keys=True,
        )


def _string_value(value: str) -> AnyValue:
    return AnyValue(string_value=value)


def _int_value(value: int) -> AnyValue:
    return AnyValue(int_value=value)


def _bool_value(value: bool) -> AnyValue:
    return AnyValue(bool_value=value)


def _key_value(key: str, value: AnyValue) -> KeyValue:
    return KeyValue(key=key, value=value)


def build_rate_schedule(rate: int, duration_seconds: int, ramp_up_seconds: int) -> list[int]:
    """Build a deterministic per-second schedule.

    Contract:
    - `rate` is the steady-state peak target for each second after ramp-up.
    - ramp-up intentionally reduces the total planned event count rather than
      compensating later with an overshoot above `rate`.
    - the returned schedule sum is therefore the authoritative planned-event
      count for the run and is what `target_events` reports.
    """
    if rate <= 0:
        raise ValueError("rate must be greater than zero")
    if duration_seconds <= 0:
        raise ValueError("duration_seconds must be greater than zero")
    if ramp_up_seconds < 0:
        raise ValueError("ramp_up_seconds must be zero or greater")
    if ramp_up_seconds >= duration_seconds:
        raise ValueError("ramp_up_seconds must be less than duration_seconds")

    schedule: list[int] = []
    for second in range(1, duration_seconds + 1):
        if ramp_up_seconds and second <= ramp_up_seconds:
            schedule.append(max(1, math.ceil(rate * second / ramp_up_seconds)))
        else:
            schedule.append(rate)
    return schedule


def _event_type(sequence_number: int) -> str:
    return EVENT_TYPES[(sequence_number - 1) % len(EVENT_TYPES)]


def _severity(sequence_number: int) -> tuple[str, int]:
    return SEVERITIES[(sequence_number - 1) % len(SEVERITIES)]


def _criticality(sequence_number: int) -> str:
    return BUSINESS_CRITICALITIES[(sequence_number - 1) % len(BUSINESS_CRITICALITIES)]


def build_log_request(
    *,
    config: WorkloadConfig,
    sequence_number: int,
    run_id: str,
    emitted_at_ns: int,
    current_rate: int,
) -> ExportLogsServiceRequest:
    severity_text, severity_number = _severity(sequence_number)
    event_type = _event_type(sequence_number)
    transaction_id = f"{run_id}-{sequence_number:08d}"
    timestamp = datetime.fromtimestamp(emitted_at_ns / 1_000_000_000, tz=UTC).isoformat()

    resource = Resource(
        attributes=[
            _key_value("service.name", _string_value(config.service_name)),
            _key_value("service.version", _string_value(config.service_version)),
            _key_value("deployment.environment", _string_value(config.environment)),
            _key_value("orion.topic", _string_value(config.topic)),
        ]
    )
    scope = InstrumentationScope(name="orion-baseline-generator", version=__version__)
    log_record = LogRecord(
        time_unix_nano=emitted_at_ns,
        observed_time_unix_nano=emitted_at_ns,
        severity_number=severity_number,
        severity_text=severity_text,
        body=_string_value(f"{event_type} synthetic event"),
        attributes=[
            _key_value("event.type", _string_value(event_type)),
            _key_value("event.sequence", _int_value(sequence_number)),
            _key_value("event.timestamp", _string_value(timestamp)),
            _key_value("event.target_rate", _int_value(current_rate)),
            _key_value("orion.transaction_id", _string_value(transaction_id)),
            _key_value("orion.business_criticality", _string_value(_criticality(sequence_number))),
            _key_value("orion.synthetic", _bool_value(True)),
            _key_value("orion.environment", _string_value(config.environment)),
            _key_value("orion.run_id", _string_value(run_id)),
        ],
    )
    return ExportLogsServiceRequest(
        resource_logs=[
            ResourceLogs(
                resource=resource,
                scope_logs=[ScopeLogs(scope=scope, log_records=[log_record])],
            )
        ]
    )


def _producer_config(config: WorkloadConfig) -> dict[str, object]:
    return {
        "bootstrap.servers": config.bootstrap_servers,
        "acks": config.acks,
        "batch.size": config.batch_size,
        "compression.type": config.compression_type,
        "linger.ms": config.linger_ms,
        "message.send.max.retries": 3,
        "message.timeout.ms": config.request_timeout_ms,
        "client.id": "orion-baseline-workload",
    }


def _run_window(
    *,
    producer: Producer,
    config: WorkloadConfig,
    current_rate: int,
    start_sequence: int,
    run_id: str,
) -> tuple[int, int]:
    sequence_number = start_sequence
    enqueued = 0
    acknowledged = 0
    failed_callbacks = 0

    def delivery_report(err, _msg) -> None:
        nonlocal acknowledged, failed_callbacks
        if err is None:
            acknowledged += 1
            return
        LOGGER.error("Kafka send failed: %s", err)
        failed_callbacks += 1

    for _ in range(current_rate):
        emitted_at_ns = time.time_ns()
        request = build_log_request(
            config=config,
            sequence_number=sequence_number,
            run_id=run_id,
            emitted_at_ns=emitted_at_ns,
            current_rate=current_rate,
        )
        produced = False
        while not produced:
            try:
                producer.produce(
                    config.topic,
                    key=f"{run_id}-{sequence_number:08d}".encode("utf-8"),
                    value=request.SerializeToString(),
                    on_delivery=delivery_report,
                )
                produced = True
                enqueued += 1
            except BufferError:
                producer.poll(0.1)
        producer.poll(0)
        sequence_number += 1

    remaining = producer.flush(timeout=max(10, math.ceil(current_rate / 500)))
    failed = max(enqueued - acknowledged, failed_callbacks + remaining)
    unresolved = max(0, failed - failed_callbacks)
    if remaining or unresolved:
        LOGGER.error(
            "%s messages remained unresolved after flush (reported queued=%s)",
            unresolved,
            remaining,
        )
    return acknowledged, failed


def run_workload(config: WorkloadConfig) -> WorkloadSummary:
    config.validate()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    if config.metrics_port:
        start_http_server(config.metrics_port)
        LOGGER.info("Started workload metrics endpoint on :%s", config.metrics_port)
    LAST_RUN_ACKNOWLEDGED.set(0)
    LAST_RUN_FAILED.set(0)

    schedule = build_rate_schedule(config.rate, config.duration_seconds, config.ramp_up_seconds)
    run_id = config.run_id or datetime.now(tz=UTC).strftime("orion-baseline-%Y%m%d%H%M%S%f")
    LOGGER.info(
        "Starting ORION baseline workload run_id=%s topic=%s duration=%ss target_rates=%s",
        run_id,
        config.topic,
        config.duration_seconds,
        schedule,
    )

    acknowledged = 0
    failed = 0
    sequence_number = 1
    started_at = time.perf_counter()

    producer = Producer(_producer_config(config))
    try:
        for second_index, current_rate in enumerate(schedule, start=1):
            TARGET_RATE.set(current_rate)
            window_started_at = time.perf_counter()
            window_acknowledged, window_failed = _run_window(
                producer=producer,
                config=config,
                current_rate=current_rate,
                start_sequence=sequence_number,
                run_id=run_id,
            )
            sequence_number += current_rate
            acknowledged += window_acknowledged
            failed += window_failed
            EVENTS_SENT.inc(window_acknowledged)
            EVENTS_FAILED.inc(window_failed)

            window_elapsed = time.perf_counter() - window_started_at
            ACTUAL_RATE.set(window_acknowledged / window_elapsed if window_elapsed > 0 else 0.0)
            remaining = 1.0 - window_elapsed
            LOGGER.info(
                "second=%s target_rate=%s acknowledged=%s failed=%s elapsed=%.3fs",
                second_index,
                current_rate,
                window_acknowledged,
                window_failed,
                window_elapsed,
            )
            if remaining > 0:
                time.sleep(remaining)
    finally:
        producer.flush(10)

    elapsed = time.perf_counter() - started_at
    LAST_RUN_DURATION.set(elapsed)
    LAST_RUN_ACKNOWLEDGED.set(acknowledged)
    LAST_RUN_FAILED.set(failed)
    summary = WorkloadSummary(
        run_id=run_id,
        target_events=sum(schedule),
        acknowledged_events=acknowledged,
        failed_events=failed,
        elapsed_seconds=elapsed,
    )
    LOGGER.info("Completed ORION baseline workload summary=%s", summary.to_json())
    return summary


def iter_log_attributes(request: ExportLogsServiceRequest) -> Iterable[KeyValue]:
    for resource_logs in request.resource_logs:
        for scope_logs in resource_logs.scope_logs:
            for log_record in scope_logs.log_records:
                yield from log_record.attributes
