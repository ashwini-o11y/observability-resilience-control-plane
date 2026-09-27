# ADR-001 — ORION Project Purpose

## Status

Accepted for discovery phase

## Context

OpenTelemetry, Dynatrace, Splunk, and other observability platforms already provide substantial capabilities for sampling, filtering, routing, queues, retries, and telemetry management.

Therefore, a project that merely implements:

```text
Kafka → OpenTelemetry → Dynatrace + Splunk
```

would not provide a sufficiently differentiated enterprise problem.

## Decision

ORION will investigate and implement an **observability resilience and telemetry control-plane problem** rather than a generic telemetry integration.

The working research question is:

> How can an enterprise preserve critical diagnostic evidence when telemetry volume spikes or the observability pipeline/backends become degraded?

The project will explicitly document existing vendor capabilities and avoid claiming that standard sampling, routing, or filtering are novel.

## Strategic positioning

ORION complements established observability platforms.

The intended value is the cross-system control-plane layer that:

- understands operational context,
- evaluates telemetry criticality,
- protects diagnostic evidence,
- coordinates resilience behaviour across heterogeneous pipelines,
- and can participate in a controlled feedback loop with an SRE intelligence layer.

## Consequences

### Positive

- Stronger enterprise problem framing
- Measurable reliability experiments
- Vendor-neutral positioning
- Natural integration with OpenTelemetry
- Natural extension point for SARI
- Clear SRE and observability resilience story

### Trade-offs

- Greater architectural complexity
- More research required before implementation
- Requires disciplined failure-injection experiments
- Some capabilities may overlap with vendor features and must be positioned carefully

## Validation requirement

Before implementing the control plane, the project must perform an existing-solutions review and establish a baseline pipeline so that the scope of ORION is evidence-driven.
