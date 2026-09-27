# ORION Success Metrics

ORION will be validated experimentally. We will not assume that the control plane improves resilience until the baseline and resilient configurations are measured under comparable failure conditions.

## Primary reliability metrics

### Critical telemetry preservation
Percentage of telemetry classified as critical that remains available during a defined failure scenario.

### Telemetry loss
Percentage of expected telemetry that is dropped or rejected.

### Diagnostic evidence availability
Percentage of the evidence required for a predefined RCA scenario that remains available during the incident.

### Recovery time
Time required for the telemetry pipeline to return to the defined healthy state after the triggering condition is removed.

## Pipeline health metrics

- Kafka consumer lag
- Kafka throughput
- Collector CPU
- Collector memory
- Collector queue depth
- Exporter queue depth
- Export failures
- Export latency
- Retry rate
- Backend availability
- Backend ingestion pressure

## Efficiency metrics

- Total telemetry processed
- Telemetry volume reduction
- Low-value telemetry suppression
- Critical telemetry overhead
- Estimated backend ingestion avoided

Any cost or savings estimate must be based on an explicit, configurable pricing assumption and must not be presented as a measured production saving.

## Experiment comparison

At minimum, experiments should compare:

1. **Baseline / naïve telemetry pipeline**
2. **Resilient ORION-controlled pipeline**

The comparison should use the same workload and failure condition.

## Target outcome

The target is not maximum telemetry retention.

The target is:

> Preserve the diagnostic evidence needed to understand critical failures while preventing observability infrastructure from becoming the next failure amplifier.

Measured targets will be defined after baseline experiments establish realistic values.
