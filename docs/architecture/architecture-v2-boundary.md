# ORION Architecture Boundary — v2 Discovery Note

## Decision boundary

The research changes the architecture emphasis:

**Do not build:** a replacement sampling/filtering/queueing engine.

**Investigate:** a control plane that observes the state of the telemetry data plane and backend destinations, evaluates enterprise policy, and coordinates existing controls.

## Candidate control loop

```text
Application / Kafka / Collector / Backend signals
                    |
                    v
             ORION Health Model
                    |
                    v
           Policy + Criticality
                    |
                    v
             Decision Engine
                    |
        +-----------+-----------+
        |           |           |
        v           v           v
     OTel       Routing      Backend
     policy     policy       selection
        |           |           |
        +-----------+-----------+
                    |
                    v
             Observe outcome
                    |
                    v
              Audit + SARI
```

## Important constraint

The control plane must remain optional to the application execution path. If ORION is unavailable, the data plane must fall back to safe preconfigured behaviour.

## What the baseline must prove

Before implementing this loop, the project must measure what happens when the same workload is run through a conventional OTel pipeline and when equivalent existing OTel/vendor controls are applied.

Only the measurable gap should become ORION functionality.
