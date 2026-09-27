#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

SMOKE_RATE="${SMOKE_RATE:-5}"
SMOKE_DURATION="${SMOKE_DURATION:-2}"
SMOKE_RAMP_UP="${SMOKE_RAMP_UP:-0}"
FAILED=1

cleanup() {
  if (( FAILED != 0 )); then
    echo "--- docker compose ps ---" >&2
    docker compose ps >&2 || true
    echo "--- kafka logs ---" >&2
    docker compose logs --tail=120 kafka >&2 || true
    echo "--- collector logs ---" >&2
    docker compose logs --tail=200 otel-collector >&2 || true
    echo "--- exported logs tail ---" >&2
    tail -n 40 artifacts/collector/exported-logs.jsonl >&2 || true
  fi
  make clean >/dev/null 2>&1 || true
}
trap cleanup EXIT

make clean >/dev/null 2>&1 || true
make start

measurement_json="$(
  RATE="${SMOKE_RATE}" \
  DURATION="${SMOKE_DURATION}" \
  RAMP_UP="${SMOKE_RAMP_UP}" \
  ./scripts/measure-baseline.sh
)"

printf '%s\n' "${measurement_json}" > artifacts/measurements/smoke-test.json

python3 - <<'PY' "${measurement_json}"
import json
import sys

measurement = json.loads(sys.argv[1])
target = measurement["workload_target_records"]
acks = measurement["workload_acknowledged_records"]

assert target > 0, "expected a positive target record count"
assert acks == target, f"expected workload acknowledgements ({acks}) to equal target ({target})"
assert measurement["workload_failed_records"] == 0, "expected workload failed count to be zero"
assert measurement["kafka_log_end_offset_delta"] >= acks, "expected Kafka log-end delta to include all workload records"
assert measurement["kafka_consumer_current_offset_delta"] >= acks, "expected collector consumer offsets to advance by all workload records"
assert measurement["otel_receiver_accepted_delta"] >= acks, "expected collector receiver metric to include all workload records"
assert measurement["otel_exporter_debug_sent_delta"] >= acks, "expected debug exporter metric to include all workload records"
assert measurement["otel_exporter_file_sent_delta"] >= acks, "expected file exporter metric to include all workload records"
assert measurement["kafka_consumer_lag_total"] == 0, "expected Kafka consumer lag to return to zero"
PY

echo "Smoke test passed: ${measurement_json}"
FAILED=0
