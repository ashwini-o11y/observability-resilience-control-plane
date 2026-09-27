# Vendor Capability Sources — Discovery Notes

Research date: 2026-09-27

## OpenTelemetry

- Collector processor catalogue includes memory limiting, probabilistic sampling, tail sampling, adaptive tail sampling, batching, filtering and transformation.
- Collector ecosystem also includes routing and load-balancing components.

Primary source: https://opentelemetry.io/docs/collector/components/processor/

## Dynatrace

- Adaptive Traffic Management automatically adjusts trace sampling to manage captured trace volume.
- Dynatrace documents OpenTelemetry Collector head and tail sampling.
- Current Dynatrace documentation also describes fixed-rate sampling for defined scopes.

Primary sources:
- https://docs.dynatrace.com/docs/ingest-from/opentelemetry/collector/use-cases/sampling
- https://docs.dynatrace.com/docs/ingest-from/dynatrace-oneagent/adaptive-traffic-management
- https://docs.dynatrace.com/docs/ingest-from/dynatrace-oneagent/adaptive-traffic-management/adaptive-traffic-management-concepts

## Splunk

- Splunk Distribution of OpenTelemetry Collector includes memory limiting, probabilistic sampling, tail sampling, filtering and transformation.
- Exporters support queued retry; supported Collector deployments can use persistent queues.
- Collector pipelines can use multiple exporters/connectors and routing mechanisms.

Primary sources:
- https://help.splunk.com/en/splunk-observability-cloud/manage-data/splunk-distribution-of-the-opentelemetry-collector/get-started-with-the-splunk-distribution-of-the-opentelemetry-collector/collector-components/processors
- https://help.splunk.com/en/splunk-observability-cloud/manage-data/splunk-distribution-of-the-opentelemetry-collector/get-started-with-the-splunk-distribution-of-the-opentelemetry-collector/collector-for-kubernetes/advanced-configuration
- https://help.splunk.com/en/splunk-observability-cloud/manage-data/splunk-distribution-of-the-opentelemetry-collector/get-started-with-the-splunk-distribution-of-the-opentelemetry-collector/collector-components/exporters/otlphttp-exporter

## Elastic

- Elastic supports native APM Server tail-based sampling.
- Elastic also documents OpenTelemetry Collector tail sampling and limitations around downstream metric extrapolation.

Primary sources:
- https://www.elastic.co/docs/solutions/observability/apm/apm-server/tail-based-sampling
- https://www.elastic.co/docs/solutions/observability/apm/opentelemetry/limitations

## Datadog

- Datadog documents OpenTelemetry Collector tail-based and probabilistic sampling.
- Datadog notes the requirement for all spans of a trace to reach the same Collector for effective tail sampling.

Primary source: https://docs.datadoghq.com/opentelemetry/ingestion_sampling/

## Grafana Alloy

- Alloy supports probabilistic sampling and tail sampling through OpenTelemetry Collector components.
- Grafana documents stateful tail sampling and scaling considerations.

Primary sources:
- https://grafana.com/docs/alloy/latest/reference/components/otelcol/otelcol.processor.probabilistic_sampler/
- https://grafana.com/docs/alloy/latest/reference/components/otelcol/otelcol.processor.tail_sampling/
- https://grafana.com/docs/opentelemetry/collector/sampling/scale/

## Research interpretation

The common capability layer is already mature. The open question for ORION is therefore coordination across heterogeneous telemetry systems and operational contexts, not the invention of another sampler or queue.
