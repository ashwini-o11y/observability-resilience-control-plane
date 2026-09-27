# ORION — Observability Resilience & Intelligent Operations Network

ORION is an enterprise observability resilience control plane designed to protect critical diagnostic telemetry during application incidents, telemetry storms, observability-pipeline failures, and backend degradation.

## Product thesis

The most dangerous time to lose observability evidence is when an incident is already underway.

ORION investigates and implements a vendor-neutral control plane that can preserve high-value telemetry under operational stress while working with existing OpenTelemetry and observability platforms such as Dynatrace, Splunk, Elastic, Grafana, and others.

ORION is designed to **complement, not replace, existing observability platforms**.

## Problem

A common failure pattern is:

Application degradation
→ telemetry volume increases
→ Kafka / OpenTelemetry / backend pressure increases
→ telemetry is delayed or dropped
→ diagnostic evidence decreases
→ root-cause analysis becomes harder
→ operational risk increases

ORION aims to break that feedback loop by making telemetry-management decisions based on operational context and system health.

## Current status

**Phase:** Foundation / Discovery progressing into baseline lab implementation

No production ORION control-plane implementation has been started yet. The first implementation delivered in this repository is the reproducible baseline experiment environment used to validate the problem, establish measurements, and prepare later resilience experiments before introducing automation.

## Local baseline lab

The repository now includes the reproducible **baseline/control** lab environment for Experiment 001:

```text
Demo workload → Kafka → OpenTelemetry Collector → backend export interfaces
```

Quickstart:

```bash
make start
make generate RATE=100 DURATION=30
make status
```

See `docs/baseline-lab.md` for setup, workload generation, Kafka/collector inspection, optional Dynatrace/Splunk configuration, troubleshooting, and cleanup.

## Planned capability areas

- Telemetry pressure and pipeline-health awareness
- Criticality and priority classification
- Policy-driven telemetry protection
- Graceful degradation under pressure
- Multi-backend routing and resilience
- Failure injection and reliability experiments
- SARI-assisted anomaly detection and root-cause analysis
- Closed-loop telemetry control
- Enterprise security, governance, auditability, and policy versioning

## Engineering approach

ORION will be developed as an experiment-driven engineering project:

1. Discover and validate the problem.
2. Research existing capabilities.
3. Establish a measurable baseline.
4. Inject controlled failures.
5. Design resilience mechanisms.
6. Implement and compare against the baseline.
7. Add closed-loop intelligence.
8. Harden for enterprise use.

## Repository roadmap

- **M1 — Foundation:** Product definition, research, requirements, architecture, ADRs
- **M2 — Baseline:** Kafka, demo services, OpenTelemetry, Dynatrace/Splunk
- **M3 — Failure Engineering:** Telemetry storms, lag, collector and backend failures
- **M4 — Resilience:** Prioritization, backpressure, graceful degradation and recovery
- **M5 — Intelligent Control Plane:** Policy and decision engines
- **M6 — SARI:** Closed-loop anomaly detection, RCA and telemetry control
- **M7 — Enterprise Hardening:** Security, HA, Kubernetes, Terraform, CI/CD, governance
- **M8 — Productization:** Dashboards, benchmarks, documentation, demo and enterprise use cases

## Status

This repository is intentionally starting with architecture and product discovery rather than application code.

## License

Licensing has not yet been selected. This will be decided deliberately as part of the product strategy.
