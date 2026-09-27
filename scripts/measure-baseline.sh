#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

COMPOSE="${COMPOSE:-docker compose}"
TOPIC="${TOPIC:-orion.baseline.telemetry.logs.v1}"
CONSUMER_GROUP="${CONSUMER_GROUP:-orion-baseline-collector}"
RATE="${RATE:-10}"
DURATION="${DURATION:-2}"
RAMP_UP="${RAMP_UP:-0}"
RUN_ID="${RUN_ID:-}"
MEASURE_TIMEOUT="${MEASURE_TIMEOUT:-90}"
ARTIFACT_DIR="${ARTIFACT_DIR:-artifacts/measurements}"

mkdir -p "${ARTIFACT_DIR}" artifacts/workload

metric_sum() {
  local pattern="$1"
  curl -fsS http://localhost:8888/metrics | awk -v pattern="${pattern}" '$0 ~ pattern {sum += $NF} END {print int(sum + 0)}'
}

kafka_log_end_total() {
  ${COMPOSE} exec -T kafka kafka-get-offsets --bootstrap-server kafka:9092 --topic "${TOPIC}" \
    | awk -F: '{sum += $3} END {print int(sum + 0)}'
}

consumer_group_totals() {
  local output
  output="$(${COMPOSE} exec -T kafka kafka-consumer-groups --bootstrap-server kafka:9092 --describe --group "${CONSUMER_GROUP}" 2>/dev/null || true)"
  if [[ -z "${output}" ]]; then
    echo "0 0 0"
    return 0
  fi

  awk '
    NR > 1 && NF >= 6 {
      current += $4
      log_end += $5
      lag += $6
    }
    END {
      printf "%d %d %d\n", int(current + 0), int(log_end + 0), int(lag + 0)
    }
  ' <<< "${output}"
}

wait_for_pipeline_accounting() {
  local run_id="$1"
  local expected_records="$2"
  local receiver_before="$3"
  local debug_before="$4"
  local file_before="$5"
  local deadline=$((SECONDS + MEASURE_TIMEOUT))

  while (( SECONDS < deadline )); do
    local receiver_after debug_after file_after
    receiver_after="$(metric_sum '^otelcol_receiver_accepted_log_records\\{receiver=\"kafka\"')"
    debug_after="$(metric_sum '^otelcol_exporter_sent_log_records\\{exporter=\"debug\"')"
    file_after="$(metric_sum '^otelcol_exporter_sent_log_records\\{exporter=\"file\"')"

    local receiver_delta=$((receiver_after - receiver_before))
    local debug_delta=$((debug_after - debug_before))
    local file_delta=$((file_after - file_before))

    if (( receiver_delta >= expected_records && debug_delta >= expected_records && file_delta >= expected_records )) \
      && grep -Fq "${run_id}" artifacts/collector/exported-logs.jsonl 2>/dev/null; then
      return 0
    fi

    sleep 2
  done

  return 1
}

./scripts/wait-for-baseline.sh >/dev/null

before_kafka_log_end="$(kafka_log_end_total)"
read -r before_consumer_current before_consumer_log_end before_consumer_lag < <(consumer_group_totals)
before_receiver="$(metric_sum '^otelcol_receiver_accepted_log_records\\{receiver=\"kafka\"')"
before_debug="$(metric_sum '^otelcol_exporter_sent_log_records\\{exporter=\"debug\"')"
before_file="$(metric_sum '^otelcol_exporter_sent_log_records\\{exporter=\"file\"')"

run_output="$(make --no-print-directory generate RATE="${RATE}" DURATION="${DURATION}" RAMP_UP="${RAMP_UP}" RUN_ID="${RUN_ID}" 2>&1)"
printf '%s\n' "${run_output}" > artifacts/workload/latest-generate.log
summary_json="$(printf '%s\n' "${run_output}" | tail -n 1)"
printf '%s\n' "${summary_json}" > artifacts/workload/latest-summary.json

mapfile -t summary_fields < <(
  python3 - <<'PY' "${summary_json}"
import json
import sys

summary = json.loads(sys.argv[1])
for key in (
    "run_id",
    "target_events",
    "acknowledged_events",
    "failed_events",
    "achieved_rate",
    "elapsed_seconds",
):
    print(summary[key])
PY
)
run_id="${summary_fields[0]}"
target_events="${summary_fields[1]}"
acknowledged_events="${summary_fields[2]}"
failed_events="${summary_fields[3]}"
achieved_rate="${summary_fields[4]}"
elapsed_seconds="${summary_fields[5]}"

if ! wait_for_pipeline_accounting "${run_id}" "${acknowledged_events}" "${before_receiver}" "${before_debug}" "${before_file}"; then
  echo "ERROR: collector/file exporter did not observe run ${run_id} within ${MEASURE_TIMEOUT}s" >&2
  echo "--- workload output ---" >&2
  printf '%s\n' "${run_output}" >&2
  echo "--- collector logs ---" >&2
  ${COMPOSE} logs --tail=200 otel-collector >&2 || true
  exit 1
fi

after_kafka_log_end="$(kafka_log_end_total)"
read -r after_consumer_current after_consumer_log_end after_consumer_lag < <(consumer_group_totals)
after_receiver="$(metric_sum '^otelcol_receiver_accepted_log_records\\{receiver=\"kafka\"')"
after_debug="$(metric_sum '^otelcol_exporter_sent_log_records\\{exporter=\"debug\"')"
after_file="$(metric_sum '^otelcol_exporter_sent_log_records\\{exporter=\"file\"')"

measurement_json="$(
  python3 - <<'PY' \
    "${run_id}" \
    "${target_events}" \
    "${acknowledged_events}" \
    "${failed_events}" \
    "${achieved_rate}" \
    "${elapsed_seconds}" \
    "${before_kafka_log_end}" \
    "${after_kafka_log_end}" \
    "${before_consumer_current}" \
    "${after_consumer_current}" \
    "${after_consumer_lag}" \
    "${before_receiver}" \
    "${after_receiver}" \
    "${before_debug}" \
    "${after_debug}" \
    "${before_file}" \
    "${after_file}"
import json
import sys

(
    run_id,
    target_events,
    acknowledged_events,
    failed_events,
    achieved_rate,
    elapsed_seconds,
    before_kafka_log_end,
    after_kafka_log_end,
    before_consumer_current,
    after_consumer_current,
    after_consumer_lag,
    before_receiver,
    after_receiver,
    before_debug,
    after_debug,
    before_file,
    after_file,
) = sys.argv[1:]

payload = {
    "run_id": run_id,
    "workload_target_records": int(target_events),
    "workload_acknowledged_records": int(acknowledged_events),
    "workload_failed_records": int(failed_events),
    "workload_achieved_rate": float(achieved_rate),
    "workload_elapsed_seconds": float(elapsed_seconds),
    "kafka_log_end_offset_delta": int(after_kafka_log_end) - int(before_kafka_log_end),
    "kafka_consumer_current_offset_delta": int(after_consumer_current) - int(before_consumer_current),
    "kafka_consumer_lag_total": int(after_consumer_lag),
    "otel_receiver_accepted_delta": int(after_receiver) - int(before_receiver),
    "otel_exporter_debug_sent_delta": int(after_debug) - int(before_debug),
    "otel_exporter_file_sent_delta": int(after_file) - int(before_file),
    "accounting_note": "Kafka offsets and collector metrics are reported as deltas across the measurement window. On a clean stack this approximates per-run counts; on a reused stack they remain cumulative counters with per-window deltas.",
}

print(json.dumps(payload, sort_keys=True))
PY
)"

printf '%s\n' "${measurement_json}" > "${ARTIFACT_DIR}/latest-measurement.json"
printf '%s\n' "${measurement_json}"
