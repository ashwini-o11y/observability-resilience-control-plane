# ORION Architecture v3 — Baseline Lab Environment

## Scope

This document describes the implemented **baseline/control** environment for ORION Experiment 001.

It intentionally stops at the conventional telemetry data path and does **not** introduce ORION policy, decision, routing, SARI, or autonomous control logic.

## Implemented local data path

```text
Demo workload
  → Kafka topic `orion.baseline.telemetry.logs.v1`
  → OpenTelemetry Collector
  → local debug/file exporters
  → optional Dynatrace / Splunk exporters
```

## Implemented components

### Demo workload

- small Python generator
- deterministic sequence-based event metadata
- configurable event rate, duration, and ramp-up
- emits OTLP log envelopes into Kafka
- optional Prometheus-style workload metrics endpoint during a run

### Kafka

- single-node local broker
- 3 partitions
- replication factor 1
- topic auto-creation disabled
- explicit topic bootstrap for reproducibility

### OpenTelemetry Collector

- exact image: `otel/opentelemetry-collector-contrib:0.111.0`
- Kafka receiver consuming OTLP logs from the baseline topic
- memory limiter and batch processors
- health endpoint on `:13133`
- collector internal metrics endpoint on `:8888`
- always-on local debug/file exports
- optional env-driven Dynatrace (`otlphttp`) and Splunk (`splunk_hec`) exports

## Exact collector component boundary

The baseline intentionally keeps the implemented path as:

```text
Workload → Kafka → Collector kafka receiver → debug/file exporters
```

The Collector image also contains an OTLP receiver, but it is **not configured** in this baseline because the architecture under test must remain workload → Kafka → Collector rather than workload → OTLP.

The validated `0.111.0` component set used by this baseline is:

- receiver: `kafka`
- receiver present but intentionally unused: `otlp`
- processors: `memory_limiter`, `batch`
- exporters: `debug`, `file`, `otlphttp`, `splunk_hec`
- extension: `health_check`

## Measurement hooks exposed

- workload generated and acknowledged event counts
- workload target/actual rate
- Kafka topic description and consumer-group lag inspection
- collector health endpoint
- collector internal metrics for received/exported telemetry, queue behavior, and process resource usage
- local exported logs in `artifacts/collector/exported-logs.jsonl`

## Explicitly deferred

- ORION Policy Engine
- ORION Decision Engine
- adaptive telemetry control
- dynamic sampling decisions
- SARI automation
- autonomous remediation
- production Kubernetes or cloud deployment
