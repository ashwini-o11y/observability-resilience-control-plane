# ADR-002 — Existing Capabilities and ORION Differentiation Boundary

## Status

Accepted for discovery phase

## Context

The initial ORION concept included Kafka, OpenTelemetry, Dynatrace, and Splunk. Current vendor documentation shows that the ecosystem already provides mature capabilities for sampling, filtering, memory protection, routing, buffering, retry, and backend-specific telemetry-volume management.

Examples include OpenTelemetry Collector tail/probabilistic sampling and memory limiting; Dynatrace Adaptive Traffic Management; Splunk Collector sampling, memory limiting, queued retry and persistent queues; Elastic native tail-based sampling; and collector-level sampling in Datadog and Grafana Alloy.

## Decision

ORION will not claim novelty for individual telemetry-processing mechanisms.

The working differentiation hypothesis will instead be a vendor-neutral control-plane capability that coordinates telemetry policy across heterogeneous data planes and backends using operational pressure, service/business criticality, diagnostic value, and incident context.

The hypothesis is only considered validated if controlled experiments show measurable diagnostic-evidence preservation that cannot be achieved as effectively through existing vendor and OpenTelemetry controls alone.

## Consequences

### Positive

- Prevents overclaiming existing vendor capabilities
- Gives ORION a measurable research question
- Preserves vendor-neutral positioning
- Encourages integration rather than replacement of established platforms
- Creates a clear basis for failure-injection experiments

### Trade-offs

- The differentiation is not yet proven
- More vendor-specific research may be required
- Some ORION capabilities may ultimately be implemented as orchestration around existing controls rather than new telemetry-processing components
- Product scope may change after baseline experiments

## Validation plan

1. Establish a baseline Kafka → OTel → Dynatrace/Splunk pipeline.
2. Establish a reproducible telemetry-storm workload.
3. Inject pipeline and backend degradation.
4. Measure diagnostic evidence, telemetry loss, lag, resource pressure and recovery.
5. Reproduce the scenario using existing OTel/vendor controls without ORION.
6. Implement the smallest ORION control-plane capability needed to coordinate the response.
7. Repeat the experiment under equivalent conditions.
8. Compare results and document whether the control-plane hypothesis is supported.

## Evidence

See `docs/existing-solutions.md` for the current capability review and primary vendor documentation links.
