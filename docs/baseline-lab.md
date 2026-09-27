# ORION Baseline Lab Environment

## Purpose

This baseline lab implements the **control** environment for ORION Experiment 001:

```text
Demo workload → Kafka → OpenTelemetry Collector → backend export interfaces
```

The baseline is intentionally conventional and reproducible so later experiments can measure lag, pressure, exporter failure, telemetry loss, and evidence degradation before any ORION intelligence is introduced.

**This is the ORION baseline/control system. ORION resilience and adaptive-control logic is intentionally not implemented yet.**

## Architecture

- **Workload:** Python generator that publishes OTLP log envelopes to Kafka at a configurable rate.
- **Kafka:** single-node local broker with explicit topic bootstrap.
- **Collector:** OpenTelemetry Collector consuming from Kafka and exporting to local debug/file output, with optional Dynatrace and Splunk exporters controlled by environment variables.
- **Backends:** commercial integrations are optional and disabled by default.

Supporting architecture note: `docs/architecture/architecture-v3-baseline-lab.md`

## Prerequisites

- Docker with Docker Compose support
- Python 3.11+ for local test execution and collector config rendering

## Installation

Clone the repository, then optionally create a local environment file:

```bash
cp .env.example .env
```

The baseline runs without proprietary credentials. Leave Dynatrace/Splunk settings disabled unless you intentionally want to test those exporters.

## Environment variables

The baseline starts without proprietary credentials. Optional backend exports are enabled only when both the feature flag and the required backend-specific variables are set.

### Dynatrace

- `ENABLE_DYNATRACE=true`
- `DYNATRACE_OTLP_ENDPOINT=https://<tenant>/api/v2/otlp`
- `DYNATRACE_API_TOKEN=<token>`

These values are rendered into the collector configuration on the host and are also passed explicitly into the collector container environment so `${env:...}` lookups resolve inside the container.

### Splunk

- `ENABLE_SPLUNK=true`
- `SPLUNK_HEC_ENDPOINT=https://<splunk-hec-endpoint>/services/collector`
- `SPLUNK_HEC_TOKEN=<token>`
- `SPLUNK_HEC_INDEX=main`

These values are also passed explicitly into the collector container environment. If `ENABLE_SPLUNK=false`, the baseline continues to start without them.

## Startup

Start the baseline services:

```bash
make start
```

This performs two actions:

1. renders `collector/collector.generated.yaml`
2. starts Kafka, bootstraps the telemetry topic, starts the OpenTelemetry Collector, and waits for Kafka plus collector health checks to become ready

Check status:

```bash
make status
```

Follow broker and collector logs:

```bash
make logs
```

## Health checks and deterministic startup

- Kafka uses a container health check based on `kafka-topics --bootstrap-server kafka:9092 --list`
- the collector image is a minimal wrapper around `otel/opentelemetry-collector-contrib:0.111.0` that adds BusyBox only for the Docker health probe, and its container health check calls `http://localhost:13133`
- `make start` and the smoke test both call `scripts/wait-for-baseline.sh` so startup waits on actual readiness instead of fixed sleeps
- the workload service depends on `kafka-init`, which depends on Kafka health, so the generator does not start before the topic exists

## Workload generation

Generate default load:

```bash
make generate
```

Override the load profile explicitly:

```bash
make generate RATE=100 DURATION=30
make generate RATE=1000 DURATION=30
make generate RATE=5000 DURATION=30 RAMP_UP=10
make generate RATE=10000 DURATION=15 RAMP_UP=5
```

### Workload metrics during a run

`make generate` uses `docker compose run --service-ports`, so while the generator is active you can scrape:

```bash
curl http://localhost:9102/metrics
```

Useful machine-readable workload metrics include:

- `orion_workload_events_sent_total` (process lifetime counter)
- `orion_workload_events_failed_total` (process lifetime counter)
- `orion_workload_last_run_acknowledged_events`
- `orion_workload_last_run_failed_events`
- `orion_workload_target_rate_events_per_second`
- `orion_workload_actual_rate_events_per_second`
- `orion_workload_last_run_duration_seconds`

### Workload schema metadata

Each synthetic OTLP log record includes:

- `service.name`
- `service.version`
- `deployment.environment`
- `event.type`
- `event.sequence`
- `event.timestamp`
- `event.target_rate`
- `orion.transaction_id`
- `orion.business_criticality`
- `orion.synthetic`
- `orion.run_id`

The generator cycles deterministic event types, severities, and criticality labels so repeated runs preserve structure while allowing rate changes.

### Ramp-up contract

When `RAMP_UP` is non-zero, `RATE` is treated as the **steady-state peak rate** after ramp-up. The generator does **not** compensate later with an overshoot above `RATE`, so the planned event total for a ramped run is the sum of the generated per-second schedule rather than `RATE * DURATION`.

## End-to-end smoke test

Run the CI-suitable smoke test:

```bash
make smoke
```

The smoke test:

1. cleans any previous local baseline state
2. starts Kafka, topic bootstrap, and the collector
3. waits for Kafka and collector readiness
4. generates a small deterministic telemetry run
5. verifies Kafka log-end offsets increase
6. verifies the collector receiver/exporter counters increase
7. verifies the local file exporter contains the run identifier
8. prints diagnostics on failure and cleans up containers afterward

## Kafka configuration and inspection

### Topic

- **Topic name:** `orion.baseline.telemetry.logs.v1`
- **Partitions:** 3
- **Replication factor:** 1
- **Producer config:** acks=all, linger.ms=5, batch.size=65536, compression=gzip, retries=3
- **Consumer config:** group.id=`orion-baseline-collector`, client.id=`orion-baseline-kafka-receiver`, encoding=`otlp_proto`

### Inspect the topic

```bash
docker compose exec kafka kafka-topics --bootstrap-server kafka:9092 --describe --topic orion.baseline.telemetry.logs.v1
```

### Inspect consumer lag

```bash
docker compose exec kafka kafka-consumer-groups --bootstrap-server kafka:9092 --describe --group orion-baseline-collector
```

### Inspect Kafka produced records

```bash
docker compose exec kafka kafka-get-offsets --bootstrap-server kafka:9092 --topic orion.baseline.telemetry.logs.v1
```

## Collector configuration and inspection

The collector is rendered into `collector/collector.generated.yaml` and includes:

- exact image/version: `otel/opentelemetry-collector-contrib:0.111.0`
- Kafka receiver on topic `orion.baseline.telemetry.logs.v1`
- memory limiter: `limit_mib=256`, `spike_limit_mib=64`, `check_interval=1s`
- batch processor: `send_batch_size=1024`, `timeout=1s`
- health endpoint: `http://localhost:13133`
- telemetry metrics endpoint: `http://localhost:8888/metrics`
- exporters:
  - always enabled: `debug`, `file`
  - optional: `otlphttp/dynatrace`, `splunk_hec`

### Collector component compatibility

The exact collector image is validated with:

```bash
make validate-collector
```

That validation checks:

- required components exist in `otel/opentelemetry-collector-contrib:0.111.0`
- the baseline config validates against that exact image
- the optional Dynatrace and Splunk exporter config also validates against that exact image

The validation script checks that the pinned collector image still contains an `otlp` receiver, but the baseline pipeline does **not** configure or use that receiver because doing so would bypass Kafka and violate the architecture under test.

### Collector health

```bash
curl http://localhost:13133
```

### Collector metrics

```bash
curl http://localhost:8888/metrics
```

The metrics endpoint is the primary measurement path for:

- collector received/exported telemetry
- exporter success/failure
- exporter queue pressure
- collector CPU
- collector memory

Example counters:

- `otelcol_receiver_accepted_log_records`
- `otelcol_exporter_sent_log_records`

Local exported telemetry is also written to:

```text
artifacts/collector/exported-logs.jsonl
```

## Enabling Dynatrace

Set the following in `.env`:

```bash
ENABLE_DYNATRACE=true
DYNATRACE_OTLP_ENDPOINT=https://<tenant>/api/v2/otlp
DYNATRACE_API_TOKEN=<token>
```

Then restart the stack:

```bash
make start
```

## Enabling Splunk

Set the following in `.env`:

```bash
ENABLE_SPLUNK=true
SPLUNK_HEC_ENDPOINT=https://<splunk-hec-endpoint>/services/collector
SPLUNK_HEC_TOKEN=<token>
SPLUNK_HEC_INDEX=main
```

Then restart the stack:

```bash
make start
```

## Telemetry storm execution

Use the workload generator with explicit high rates:

```bash
make generate RATE=5000 DURATION=30
make generate RATE=10000 DURATION=15 RAMP_UP=5
```

This supports:

- **Experiment A:** normal load baseline
- **Experiment B:** telemetry storm and lag/pressure observation
- **Experiment C:** backend degradation observation when optional exporters are enabled or impaired externally

No adaptive behavior is implemented. Load remains operator-controlled.

## Baseline accounting and measurement

To generate workload and print baseline accounting deltas for the current run:

```bash
make measure RATE=100 DURATION=30
```

The measurement command reports:

- workload target records
- workload acknowledged records
- workload failed records
- Kafka log-end offset delta
- Kafka consumer current-offset delta
- Kafka consumer lag total
- collector receiver accepted-record delta
- collector debug exporter sent-record delta
- collector file exporter sent-record delta

### Measurement limitation

Kafka offsets and collector metrics are cumulative counters. The measurement command therefore reports **deltas across its own measurement window** rather than pretending to provide a perfect per-message ledger. On a clean stack, those deltas closely approximate the single workload run. On a reused stack, they remain valid window deltas but not globally exact totals.

## Expected behavior

- `make start` succeeds without Dynatrace or Splunk credentials.
- Kafka contains the baseline telemetry topic.
- the collector health endpoint returns a healthy response.
- `make generate` prints a JSON summary with target events, acknowledged events, failures, and achieved rate.
- collector debug output and `artifacts/collector/exported-logs.jsonl` show received workload events.

## Troubleshooting

- **`make start` fails during collector render:** confirm `python3` is available locally.
- **Kafka topic is missing:** inspect `docker compose logs kafka-init`.
- **No collector output:** confirm the workload used topic `orion.baseline.telemetry.logs.v1` and inspect `docker compose logs otel-collector`.
- **Lag is growing unexpectedly:** inspect `kafka-consumer-groups` output and collector metrics at `:8888/metrics`.
- **Smoke test fails:** inspect `artifacts/workload/latest-generate.log`, `artifacts/workload/latest-summary.json`, and `artifacts/measurements/latest-measurement.json` before cleanup or rerun `make smoke` for fresh diagnostics.
- **Optional exporters fail:** confirm credentials/endpoints are set in `.env`; the baseline still functions with local debug/file exporters.

## Cleanup

Stop services:

```bash
make stop
```

Remove volumes and local collector artifacts:

```bash
make clean
```

## Tests

Run the focused automated tests:

```bash
python3 -m pip install -e .[dev]
make test
```

Run the CI-equivalent local validation flow:

```bash
make validate-local
```

That runs:

- Python tests
- collector config rendering
- Docker Compose validation
- collector component/config validation against `otel/opentelemetry-collector-contrib:0.111.0`
- the end-to-end smoke test

## Intentionally not implemented yet

- ORION policy/decision engines
- adaptive or dynamic sampling logic
- SARI-driven control loops
- autonomous remediation
- production-grade HA Kafka or collector topology
- Kubernetes or cloud infrastructure
- failure injection automation beyond explicit operator-controlled load generation
