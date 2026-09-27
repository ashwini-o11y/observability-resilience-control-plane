# ORION Success Metrics (Draft)

## Purpose
Define measurable outcomes for observability resilience without pre-committing to implementation specifics.

## Candidate metrics

### 1) Critical telemetry preservation
- **Definition:** Percentage of designated critical telemetry retained and delivered during stress events.
- **Target direction:** Increase.

### 2) Telemetry loss
- **Definition:** Percentage of total telemetry dropped or irrecoverably delayed beyond operational usefulness.
- **Target direction:** Decrease.

### 3) Kafka lag
- **Definition:** Consumer lag and lag duration for telemetry-critical topics during steady state and incident windows.
- **Target direction:** Decrease.

### 4) Collector resource utilization
- **Definition:** CPU, memory, and queue pressure for telemetry collection/processing components.
- **Target direction:** Keep within defined guardrails during surges.

### 5) Backend availability
- **Definition:** Availability and responsiveness of observability backends for ingest and query operations.
- **Target direction:** Increase.

### 6) Recovery time
- **Definition:** Time to restore observability pipeline health and diagnostic readiness after degradation.
- **Target direction:** Decrease.

### 7) Diagnostic evidence availability
- **Definition:** Availability of required logs/metrics/traces needed for incident RCA within defined time windows.
- **Target direction:** Increase.

### 8) Telemetry volume reduction
- **Definition:** Reduction in non-critical telemetry volume during stress conditions while preserving critical evidence.
- **Target direction:** Optimize (reduce non-critical volume without harming critical signal quality).
