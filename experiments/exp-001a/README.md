# EXP-001A — Establish normal-load telemetry baseline

EXP-001A adds a repeatable experiment harness around the existing baseline architecture:

```text
Workload → Kafka → OpenTelemetry Collector → Exporter
```

It does **not** add adaptive control, policy logic, throttling, backpressure control, or other ORION behaviours. It only measures the existing baseline under operator-chosen normal load.

## Prerequisites

- Docker with `docker compose`
- Python 3.11+
- Local dependencies installed for scripts/tests:

```bash
python3 -m pip install -e .[dev]
```

## Startup

From a clean checkout:

```bash
make start
```

This renders the collector config, starts Kafka plus the collector, and waits for the baseline to become healthy.

## Run an experiment

The harness accepts operator-specified `RATE`, `DURATION`, and `RUN_ID` values. Rates are not hard-coded.

```bash
make experiment-001a RATE=100 DURATION=300 RUN_ID=exp001a-100rps-001
```

Examples for the planned comparison set:

```bash
make experiment-001a RATE=10 DURATION=300 RUN_ID=exp001a-10rps-001
make experiment-001a RATE=100 DURATION=300 RUN_ID=exp001a-100rps-001
make experiment-001a RATE=500 DURATION=300 RUN_ID=exp001a-500rps-001
make experiment-001a RATE=1000 DURATION=300 RUN_ID=exp001a-1000rps-001
```

The run command:

1. ensures the baseline stack is started
2. records environment metadata and timestamps
3. scrapes collector metrics before and after the run
4. reuses `scripts/measure-baseline.sh` to verify Workload → Kafka → OTel → Exporter
5. writes one structured JSON result per run
6. refreshes a Markdown comparison report from the available result set

## Result locations

- Per-run JSON: `experiments/exp-001a/results/<RUN_ID>.json`
- Latest generated report: `experiments/exp-001a/results/latest-report.md`
- Checked-in schema/template: `experiments/exp-001a/result-schema.json`
- Baseline artifacts reused during the run: `artifacts/collector/`, `artifacts/measurements/`, `artifacts/workload/`

Run-specific result JSON and generated reports are ignored by Git so they do not accidentally become commits.

## What is collected

Only metrics already exposed by the baseline are recorded.

- **Workload:** target records, acknowledged records, failed records, achieved rate, elapsed seconds
- **Kafka:** produced-record delta, consumer-offset delta, consumer lag
- **OTel Collector:** receiver accepted-record delta, debug/file exporter sent-record deltas, debug/file exporter failed-record deltas where exposed
- **System:** collector CPU seconds delta, collector RSS memory, collector runtime memory gauges
- **Batch/queue signals:** batch timeout/send-size counters where exposed; queue metrics remain `null` when the current collector/exporter configuration does not publish them

## Known collection limitations

- Kafka offsets and collector counters are cumulative, so EXP-001A records deltas over its measurement window rather than pretending to provide a perfect per-message ledger.
- Queue-pressure metrics are recorded only if the pinned collector image and enabled exporters expose them at `:8888/metrics`; otherwise the fields remain `null` and the result notes that limitation.
- The default local baseline exports only to the collector `debug` and `file` exporters unless optional Dynatrace or Splunk integration is intentionally enabled.

## Generate / refresh the Markdown summary

```bash
make experiment-001a-report
```

The report compares the latest available result for 10/s, 100/s, 500/s, and 1000/s when those runs exist, and it separates:

- **Observed environment behaviour** for this repository's local baseline
- **General Kafka/OTel context** disclaimers so the report does not present a universal system limit

## Interpretation

Look for:

- achieved rate versus requested rate
- non-zero Kafka lag
- differences between workload acknowledgements and collector accepted/sent counts
- non-zero exporter failure counters
- increasing collector CPU or memory
- batch timeout pressure or other first signs of degradation

Treat those findings as environment-specific observations for this baseline only.

## Stop and cleanup

Stop containers without deleting volumes:

```bash
make stop
```

Remove local volumes and baseline artifacts:

```bash
make clean
```
