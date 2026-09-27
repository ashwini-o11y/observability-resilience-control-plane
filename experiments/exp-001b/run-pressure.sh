#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${ROOT_DIR}"

PROFILE="${PROFILE:-sustained}"
RATE="${RATE:-1000}"
DURATION="${DURATION:-300}"
BASELINE_RATE="${BASELINE_RATE:-100}"
BURST_RATE="${BURST_RATE:-5000}"
BURST_DURATION="${BURST_DURATION:-60}"
RECOVERY_RATE="${RECOVERY_RATE:-100}"
RECOVERY_DURATION="${RECOVERY_DURATION:-120}"
SAMPLE_INTERVAL="${SAMPLE_INTERVAL:-5}"
RUN_ID="${RUN_ID:-exp001b-$(date -u +%Y%m%dT%H%M%SZ)}"
RESULTS_DIR="${RESULTS_DIR:-${ROOT_DIR}/experiments/exp-001b/results}"
MAX_RATE="${MAX_RATE:-10000}"
MAX_DURATION="${MAX_DURATION:-1800}"
MAX_BURST_DURATION="${MAX_BURST_DURATION:-300}"

validate_positive_int() {
  local name="$1" value="$2"
  [[ "${value}" =~ ^[0-9]+$ ]] || { echo "ERROR: ${name} must be an integer" >&2; exit 2; }
  (( value > 0 )) || { echo "ERROR: ${name} must be > 0" >&2; exit 2; }
}

validate_rate() {
  local name="$1" value="$2"
  validate_positive_int "${name}" "${value}"
  (( value <= MAX_RATE )) || { echo "ERROR: ${name}=${value} exceeds MAX_RATE=${MAX_RATE}" >&2; exit 2; }
}

validate_duration() {
  local name="$1" value="$2"
  validate_positive_int "${name}" "${value}"
  (( value <= MAX_DURATION )) || { echo "ERROR: ${name}=${value} exceeds MAX_DURATION=${MAX_DURATION}" >&2; exit 2; }
}

validate_rate RATE "${RATE}"
validate_rate BASELINE_RATE "${BASELINE_RATE}"
validate_rate BURST_RATE "${BURST_RATE}"
validate_rate RECOVERY_RATE "${RECOVERY_RATE}"
validate_positive_int SAMPLE_INTERVAL "${SAMPLE_INTERVAL}"
validate_duration DURATION "${DURATION}"
validate_duration RECOVERY_DURATION "${RECOVERY_DURATION}"
validate_duration BURST_DURATION "${BURST_DURATION}"
(( BURST_DURATION <= MAX_BURST_DURATION )) || { echo "ERROR: BURST_DURATION=${BURST_DURATION} exceeds MAX_BURST_DURATION=${MAX_BURST_DURATION}" >&2; exit 2; }

case "${PROFILE}" in
  sustained|extended|burst) ;;
  *) echo "ERROR: PROFILE must be sustained, burst, or extended" >&2; exit 2 ;;
esac

mkdir -p "${RESULTS_DIR}"
TMP_DIR="$(mktemp -d /tmp/exp-001b.XXXXXX)"
trap 'rm -rf "${TMP_DIR}"' EXIT
START_TIMESTAMP="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

make clean >/dev/null
make start

sampler() {
  local phase="$1"
  while kill -0 "${WORKLOAD_PID}" 2>/dev/null; do
    COLLECTED_AT="$(date -u +"%Y-%m-%dT%H:%M:%SZ")" "${ROOT_DIR}/experiments/exp-001b/collect-metrics.sh" 2>/dev/null \
      | python3 -c 'import json,sys; p=json.load(sys.stdin); p["phase"]=sys.argv[1]; print(json.dumps(p, sort_keys=True))' "${phase}" \
      >> "${TMP_DIR}/timeseries.jsonl" || true
    sleep "${SAMPLE_INTERVAL}"
  done
}

run_phase() {
  local phase="$1" rate="$2" duration="$3" phase_id="$4"
  echo "Running ${phase}: rate=${rate} duration=${duration}s"
  RATE="${rate}" DURATION="${duration}" RUN_ID="${phase_id}" ./scripts/measure-baseline.sh > "${TMP_DIR}/${phase_id}.measurement.json" &
  WORKLOAD_PID=$!
  sampler "${phase}" &
  SAMPLER_PID=$!
  if ! wait "${WORKLOAD_PID}"; then
    kill "${SAMPLER_PID}" 2>/dev/null || true
    wait "${SAMPLER_PID}" 2>/dev/null || true
    return 1
  fi
  wait "${SAMPLER_PID}" 2>/dev/null || true
}

STATUS="PASS"
ERROR_MESSAGE=""
PHASES_FILE="${TMP_DIR}/phases.jsonl"
: > "${TMP_DIR}/timeseries.jsonl"

case "${PROFILE}" in
  sustained)
    run_phase "sustained" "${RATE}" "${DURATION}" "${RUN_ID}-sustained" || { STATUS="FAIL"; ERROR_MESSAGE="sustained phase failed"; }
    ;;
  extended)
    run_phase "extended" "${RATE}" "${DURATION}" "${RUN_ID}-extended" || { STATUS="FAIL"; ERROR_MESSAGE="extended phase failed"; }
    ;;
  burst)
    run_phase "baseline" "${BASELINE_RATE}" "${DURATION}" "${RUN_ID}-baseline" || { STATUS="FAIL"; ERROR_MESSAGE="baseline phase failed"; }
    if [[ "${STATUS}" == "PASS" ]]; then
      run_phase "burst" "${BURST_RATE}" "${BURST_DURATION}" "${RUN_ID}-burst" || { STATUS="FAIL"; ERROR_MESSAGE="burst phase failed"; }
    fi
    if [[ "${STATUS}" == "PASS" ]]; then
      run_phase "recovery" "${RECOVERY_RATE}" "${RECOVERY_DURATION}" "${RUN_ID}-recovery" || { STATUS="FAIL"; ERROR_MESSAGE="recovery phase failed"; }
    fi
    ;;
esac

END_TIMESTAMP="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
python3 "${ROOT_DIR}/experiments/exp-001b/analyze-results.py" build \
  --experiment "EXP-001B" \
  --run-id "${RUN_ID}" \
  --profile "${PROFILE}" \
  --start-timestamp "${START_TIMESTAMP}" \
  --end-timestamp "${END_TIMESTAMP}" \
  --status "${STATUS}" \
  --error-message "${ERROR_MESSAGE}" \
  --results-dir "${RESULTS_DIR}" \
  --timeseries "${TMP_DIR}/timeseries.jsonl" \
  --measurement-dir "${TMP_DIR}" \
  --output "${RESULTS_DIR}/${RUN_ID}.json"

python3 "${ROOT_DIR}/experiments/exp-001b/analyze-results.py" report --results-dir "${RESULTS_DIR}" --output "${RESULTS_DIR}/latest-report.md"

echo "EXP-001B result: ${RESULTS_DIR}/${RUN_ID}.json"
echo "EXP-001B report: ${RESULTS_DIR}/latest-report.md"
[[ "${STATUS}" == "PASS" ]] || exit 1
