# ORION Architecture v1

## Architectural intent

ORION is designed as a control plane around an OpenTelemetry-based telemetry data plane.

### High-level model

Applications and event sources
→ Kafka / telemetry sources
→ OpenTelemetry pipeline
→ ORION policy and resilience controls
→ observability backends
→ SARI / analytics
→ feedback into the control plane

## Logical components

### 1. Telemetry sources
Applications, services, Kafka topics, infrastructure and other systems producing telemetry.

### 2. OpenTelemetry data plane
OpenTelemetry Collectors and associated receivers, processors, queues, exporters, and telemetry protocols.

### 3. ORION control plane
The control plane is expected to contain:

- Health Monitor
- Telemetry Criticality / Priority Engine
- Policy Engine
- Decision Engine
- Resilience / Degradation Manager
- Routing / Backend Awareness
- Audit Engine

### 4. Observability backends
Dynatrace, Splunk, Elastic, Grafana-compatible systems, cloud-native monitoring platforms, or other supported destinations.

### 5. Intelligence layer
SARI or another analysis engine may consume telemetry and operational state and may request higher-fidelity evidence during investigation.

## Initial reference architecture

```text
Applications / APIs / Events
           |
           v
        Kafka
           |
           v
 OpenTelemetry Collectors
           |
           v
   ORION Control Plane
   |      |      |      |
 Health  Policy  Priority  Resilience
           |
     +-----+------+
     |            |
 Dynatrace      Splunk
     |            |
     +-----+------+
           |
          SARI
           |
    investigative feedback
           |
           v
   ORION policy loop
```

## Important boundary

ORION should not be implemented as a mandatory synchronous dependency for application execution.

The application path must remain operational if ORION is unavailable.

## Architecture questions for discovery

- Which controls should remain inside OTel versus ORION?
- Which signals should be evaluated locally at the collector?
- How should policy changes propagate safely?
- How should ORION avoid becoming a centralized bottleneck?
- What failure semantics apply when a backend is unavailable?
- How should policy changes be audited and rolled back?
- How should SARI requests be bounded and authorized?

These questions will be answered through ADRs and experiments rather than assumed prematurely.
