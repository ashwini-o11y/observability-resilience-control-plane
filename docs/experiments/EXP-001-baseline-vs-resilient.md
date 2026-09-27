# EXP-001 — Baseline vs Resilient Observability Pipeline

## Status

Planned

## Objective

Determine whether a vendor-neutral control-plane layer provides measurable diagnostic-evidence preservation beyond existing OpenTelemetry/vendor controls during controlled telemetry and backend stress.

## Phase A — Baseline

Build a simple pipeline:

```text
Workload → Kafka → OpenTelemetry Collector → Dynatrace + Splunk
```

Capture:

- workload rate
- telemetry rate
- Kafka lag
- Collector CPU/memory/queue pressure
- exporter failures/retries
- backend response/availability
- telemetry loss
- diagnostic evidence availability
- recovery time

## Phase B — Failure injection

Introduce controlled:

1. telemetry-volume spike
2. Kafka consumer lag
3. Collector resource pressure
4. Dynatrace degradation/unavailability
5. Splunk degradation/unavailability

## Phase C — Existing controls

Repeat the scenarios using appropriate OpenTelemetry and/or vendor-native controls without ORION.

Examples may include:

- memory limiter
- probabilistic sampling
- tail sampling
- exporter queue/retry
- routing
- vendor-specific sampling controls

The exact configuration will be documented before execution.

## Phase D — ORION treatment

Implement only the smallest control-plane capability required by the validated gap.

The initial treatment is expected to evaluate operational pressure + service criticality + diagnostic value when selecting or coordinating telemetry controls.

## Primary comparison

The important question is not whether ORION reduces telemetry volume.

The important question is whether ORION preserves a greater proportion of **diagnostic evidence required for a predefined RCA scenario** under equivalent failure conditions while maintaining acceptable pipeline health.

## Guardrails

- Experiments run in an isolated/non-production environment.
- No production credentials or customer telemetry.
- Failure injection must have explicit start/stop conditions.
- ORION must not become a synchronous dependency for application execution.
- Every automated policy change must be auditable and reversible.
