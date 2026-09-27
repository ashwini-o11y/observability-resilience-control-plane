# EXP-001B — Telemetry Pressure and Degradation Characterization

EXP-001B extends the EXP-001A baseline harness to characterize telemetry pressure without implementing ORION control logic.

## Profiles

The runner supports three operator-selected profiles:

- `sustained`: one continuous load phase.
- `burst`: baseline → burst → recovery phases.
- `extended`: one longer continuous load phase.

No full pressure matrix is executed by the tooling PR. The runner is intentionally parameterized so the experiment matrix can be selected after review.

## Safety limits

The runner refuses configurations above these explicit local limits unless the script is changed intentionally:

- `MAX_RATE=10000` events/sec
- `MAX_DURATION=1800` seconds per phase
- `MAX_BURST_DURATION=300` seconds
- `SAMPLE_INTERVAL>=1` second

These are guardrails for accidental operator input, not measured capacity limits.

## Examples

```bash
PROFILE=sustained RATE=2000 DURATION=300 RUN_ID=exp001b-sustained-2000rps-001 ./experiments/exp-001b/run-pressure.sh
```

```bash
PROFILE=burst BASELINE_RATE=100 BURST_RATE=5000 BURST_DURATION=60 RECOVERY_RATE=100 RECOVERY_DURATION=120 RUN_ID=exp001b-burst-001 ./experiments/exp-001b/run-pressure.sh
```

```bash
PROFILE=extended RATE=1000 DURATION=900 RUN_ID=exp001b-extended-1000rps-001 ./experiments/exp-001b/run-pressure.sh
```

## Measurements

The runner reuses the existing `experiments/exp-001a/collect-metrics.sh` snapshot collector and records periodic snapshots during each phase. Measurements include workload accounting, Kafka offsets/lag, OTel receiver/exporter counters, queue/batch metrics when exposed, and collector CPU/memory.

Unavailable metrics remain `null` and are listed under `limitations`.

## Interpretation rules

Results distinguish observed measurements from interpretation. A pressure signal is not automatically a failure threshold, and this experiment must not claim a universal Kafka, Collector, or exporter capacity limit.

The output is written to `experiments/exp-001b/results/` and is treated as generated experiment data.
