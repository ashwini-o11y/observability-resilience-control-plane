# Existing Solutions Review

**Status:** Discovery in progress

ORION must not claim novelty for capabilities that are already provided by OpenTelemetry or commercial observability platforms.

## Capabilities to investigate

### OpenTelemetry

Review:

- Sampling and tail sampling
- Filtering and transform processors
- Memory limiting
- Batch processing
- Queues and retry behaviour
- Load balancing and routing
- Collector scaling patterns
- Dynamic configuration mechanisms

### Dynatrace

Review:

- Adaptive and tail-based sampling capabilities
- Ingestion controls
- Data retention and routing controls
- Pipeline health and monitoring
- Cost / volume controls
- Automation and configuration APIs

### Splunk

Review:

- Ingestion controls
- Sampling and filtering
- Routing
- Queues and buffering
- Indexing controls
- Observability pipeline capabilities
- Cost / volume controls

### Other platforms

Where relevant, compare Elastic, Datadog, Grafana ecosystem components, and cloud-native observability services.

## Research questions

1. Which individual capabilities already solve parts of the ORION problem?
2. Which capabilities are local to a collector/backend versus coordinated across systems?
3. Which capabilities understand application or business criticality?
4. Which capabilities coordinate decisions across heterogeneous backends?
5. Which capabilities preserve diagnostic evidence during simultaneous pipeline pressure and backend degradation?
6. Which controls can safely be automated and rolled back?
7. Where does a vendor-neutral control-plane layer add measurable value?

## Positioning rule

ORION should only claim differentiation after these capabilities have been documented and tested. The goal is to identify a real systems problem, not to manufacture novelty.

## Next step

Populate this document with current vendor documentation and repeatable experiments before finalizing the ORION control-plane boundary.
