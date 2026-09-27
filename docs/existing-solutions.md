# ORION Existing-Solutions Analysis

**Research date:** 2026-09-27

## Purpose

This document tests the ORION product thesis against current capabilities in OpenTelemetry and major observability platforms. The goal is not to claim that existing products cannot sample, filter, buffer, route, or protect telemetry. They clearly can.

The key question is narrower:

> Is there a defensible cross-vendor control-plane problem around preserving diagnostic evidence across heterogeneous telemetry pipelines during operational stress?

This is a discovery artifact, not a competitive scorecard.

## Executive finding

The basic Kafka → OpenTelemetry → Dynatrace/Splunk pipeline is **not novel**. OpenTelemetry already provides processors for filtering, memory limiting, probabilistic sampling, tail sampling, batching, routing, and queueing. Dynatrace provides adaptive trace sampling and OpenTelemetry Collector sampling guidance. Splunk's OpenTelemetry distribution provides filtering, probabilistic and tail sampling, memory limiting, queued retry, persistent queues, and multiple exporters. Elastic provides native tail-based sampling as well as Collector-based options. Datadog documents collector-level tail-based and probabilistic sampling. Grafana Alloy supports probabilistic and tail sampling.

Therefore ORION will **not** position sampling, routing, buffering, or Kafka/OTel integration by itself as the innovation.

The current product hypothesis is instead a **cross-vendor observability-resilience control plane** that coordinates policy using operational context and diagnostic criticality across heterogeneous data planes and backends. This remains a hypothesis that must be validated experimentally and against additional vendor capabilities.

## Capability matrix

| Capability | OpenTelemetry | Dynatrace | Splunk | Elastic | Datadog | Grafana/Alloy |
|---|---|---|---|---|---|---|
| Filtering / transformation | Yes | Via OTel Collector guidance and platform controls | Yes | Yes | Yes via Collector | Yes |
| Probabilistic / head sampling | Yes | Adaptive Traffic Management / head sampling | Yes | Yes | Yes | Yes |
| Tail sampling | Yes | OTel Collector supported | Yes | Native APM Server + OTel option | Collector-level | Yes |
| Memory protection | Memory limiter | Collector-based | Memory limiter | Platform-specific | Collector-based | Collector-based |
| Queues / retry | Exporter queues and retry patterns | Collector/export path | Exporter queues, retry, persistent queues in supported deployments | Backend / agent mechanisms | Collector/export mechanisms | Collector/export mechanisms |
| Routing / multiple destinations | Routing connector, exporters | Supported through OTel integrations | Routing and multiple exporters through Collector | Multiple outputs / integrations | Collector integrations | Routing/components |
| Adaptive / dynamic vendor-specific controls | Component ecosystem evolving | Strong vendor-specific adaptive sampling | Collector configuration and platform controls | Native backend sampling controls | Ingestion/sampling controls | Collector configuration |

This table deliberately avoids declaring one vendor "best". It identifies capabilities that already exist and therefore should not be presented as ORION's invention.

## OpenTelemetry

OpenTelemetry Collector processors already cover many mechanisms that an initial ORION design might otherwise duplicate. The official processor catalogue includes memory limiting, probabilistic sampling, tail sampling, adaptive tail sampling, batching, filtering and transformation components. The Collector ecosystem also includes routing and load-balancing components.

This means ORION should not become another generic Collector processor without a strong reason. The more interesting architectural boundary is a control plane that can reason about operational state and coordinate policies across multiple Collector/data-plane instances and heterogeneous destinations.

## Dynatrace

Dynatrace has substantial native telemetry-volume controls. Its Adaptive Traffic Management automatically adjusts trace sampling to keep captured trace volume around configured/licensed limits. Dynatrace also documents OpenTelemetry Collector sampling using head and tail sampling and supports fixed-rate sampling for defined scopes in its current platform documentation.

This is important because an ORION claim such as "automatically adjust sampling to control telemetry volume" would overlap directly with existing Dynatrace functionality.

The ORION hypothesis therefore needs to be broader and vendor-neutral: make policy decisions based on cross-system operational conditions and diagnostic criticality, then coordinate the appropriate mechanisms in the underlying data planes and backends.

## Splunk

Splunk's OpenTelemetry distribution includes memory limiting, probabilistic sampling, tail sampling, filtering, transformation, routing/connectors, and exporters with queued retry. Splunk also documents persistent queues for supported Collector deployments.

Therefore "protect the Collector from overload" and "queue telemetry when a backend is unavailable" are existing capabilities, not ORION-specific innovations.

The potential ORION boundary is coordination: deciding which telemetry should be protected, degraded, rerouted, or temporarily retained when multiple systems are under pressure, especially when the enterprise uses more than one backend.

## Elastic

Elastic supports tail-based sampling natively in APM Server and also documents OpenTelemetry Collector tail sampling. Elastic explicitly notes trade-offs around metric accuracy when Collector tail sampling is used and recommends its native APM Server implementation for some scenarios.

This reinforces an important ORION design principle: the system must understand the semantic consequences of telemetry controls, not only reduce bytes. Preserving diagnostic evidence must include awareness of downstream metric and correlation effects.

## Datadog

Datadog documents OpenTelemetry Collector-level tail-based and probabilistic sampling, including advanced rules for preserving visibility into traces with errors or high latency. Datadog also documents limitations when a trace is distributed across multiple Collector instances.

Again, error/latency-aware sampling is not unique to ORION. A differentiator cannot simply be "keep error traces."

## Grafana / Alloy

Grafana Alloy supports both probabilistic and tail sampling through OpenTelemetry Collector components. Grafana's documentation highlights the stateful nature of tail sampling and provides guidance for scaling the collector as telemetry volume increases.

This provides another example of mature ecosystem support for sampling and scaling, and strengthens the case for keeping ORION above rather than inside a single vendor's Collector distribution.

## What is NOT our differentiation

ORION will not claim novelty for:

- Kafka → OTel integration
- OTel → Dynatrace export
- OTel → Splunk export
- Head/probabilistic sampling
- Tail sampling
- Filtering
- Memory limiting
- Exporter queues
- Retry logic
- Basic routing
- Keeping error traces
- Reducing telemetry volume
- A generic observability dashboard

These are established capabilities.

## Current ORION differentiation hypothesis

The working hypothesis is a **vendor-neutral observability resilience control plane** that sits above the telemetry data plane and can coordinate policy based on:

1. **Operational pressure** — Kafka lag, collector pressure, exporter failures, backend degradation, incident state.
2. **Business/service criticality** — critical services, transaction classes, environments, SLO impact and other enterprise context.
3. **Diagnostic value** — telemetry needed to prove or investigate a failure, rather than simply telemetry that is statistically representative.
4. **Heterogeneous backends** — Dynatrace, Splunk and potentially other destinations with different capabilities and failure states.
5. **Controlled operating modes** — observe-only, recommend, human approval, and automated control.
6. **Closed-loop investigation** — SARI or another intelligence layer can request higher-fidelity evidence during an investigation, subject to policy and authorization.
7. **Measured resilience** — the product must prove that it preserves diagnostic evidence under failure scenarios compared with a baseline.

None of these points should yet be presented as an industry-first claim. The project must test how much of this can already be achieved through combinations of vendor capabilities.

## The key product question

The most important experiment is therefore not:

> "Can ORION sample telemetry?"

It is:

> "Can a vendor-neutral control plane improve diagnostic evidence preservation across heterogeneous observability systems during a controlled incident without becoming another failure domain?"

If the answer is yes, and the improvement cannot be achieved cleanly with existing platform controls alone, that becomes the strongest basis for ORION's product differentiation.

## Evidence sources

- OpenTelemetry Collector processor catalogue: https://opentelemetry.io/docs/collector/components/processor/
- Dynatrace sampling with OpenTelemetry Collector: https://docs.dynatrace.com/docs/ingest-from/opentelemetry/collector/use-cases/sampling
- Dynatrace Adaptive Traffic Management: https://docs.dynatrace.com/docs/ingest-from/dynatrace-oneagent/adaptive-traffic-management
- Dynatrace Adaptive Traffic Management concepts: https://docs.dynatrace.com/docs/ingest-from/dynatrace-oneagent/adaptive-traffic-management/adaptive-traffic-management-concepts
- Splunk Collector processors: https://help.splunk.com/en/splunk-observability-cloud/manage-data/splunk-distribution-of-the-opentelemetry-collector/get-started-with-the-splunk-distribution-of-the-opentelemetry-collector/collector-components/processors
- Splunk Collector advanced configuration / persistent queues: https://help.splunk.com/en/splunk-observability-cloud/manage-data/splunk-distribution-of-the-opentelemetry-collector/get-started-with-the-splunk-distribution-of-the-opentelemetry-collector/collector-for-kubernetes/advanced-configuration
- Elastic tail-based sampling: https://www.elastic.co/docs/solutions/observability/apm/apm-server/tail-based-sampling
- Elastic OpenTelemetry limitations: https://www.elastic.co/docs/solutions/observability/apm/opentelemetry/limitations
- Datadog ingestion sampling with OpenTelemetry: https://docs.datadoghq.com/opentelemetry/ingestion_sampling/
- Grafana Alloy tail sampling: https://grafana.com/docs/alloy/latest/reference/components/otelcol/otelcol.processor.tail_sampling/
- Grafana Alloy sampling overview: https://grafana.com/docs/opentelemetry/collector/sampling/
