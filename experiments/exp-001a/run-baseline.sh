#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${ROOT_DIR}"

RATE="${RATE:-10}"
DURATION="${DURATION:-30}"
RUN_ID="${RUN_ID:-exp001a-$(date -u +"%Y%m%dT%H%M%SZ")-${RATE}rps}"
RESULTS_DIR="${RESULTS_DIR:-${ROOT_DIR}/experiments/exp-001a/results}"
REPORT_OUTPUT="${REPORT_OUTPUT:-${RESULTS_DIR}/latest-report.md}"
EXPERIMENT="EXP-001A"
TMP_DIR="$(mktemp -d /tmp/exp-001a.XXXXXX)"
STATUS="PASS"
ERROR_MESSAGE=""

cleanup() {
  rm -rf "${TMP_DIR}"
}
trap cleanup EXIT

mkdir -p "${RESULTS_DIR}"

collect_environment() {
  python3 - <<'PY'
import json
import os
import platform
import subprocess

def run(*command: str) -> str | None:
    try:
        return subprocess.check_output(command, text=True).strip()
    except Exception:
        return None

payload = {
    "git_commit_sha": run("git", "rev-parse", "HEAD"),
    "git_branch": run("git", "rev-parse", "--abbrev-ref", "HEAD"),
    "platform": platform.platform(),
    "python_version": platform.python_version(),
    "docker_compose_version": run("docker", "compose", "version", "--short"),
    "docker_server_version": run("docker", "version", "--format", "{{.Server.Version}}"),
    "collector_image": "orion-baseline-collector:0.111.0",
    "kafka_image": "confluentinc/cp-kafka:7.7.1",
    "optional_exporters": {
        "dynatrace_enabled": os.environ.get("ENABLE_DYNATRACE", "false"),
        "splunk_enabled": os.environ.get("ENABLE_SPLUNK", "false"),
    },
}
print(json.dumps(payload, indent=2, sort_keys=True))
PY
}

START_TIMESTAMP="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
collect_environment > "${TMP_DIR}/environment.json"

make clean >/dev/null
make start
COLLECTED_AT="${START_TIMESTAMP}" "${ROOT_DIR}/experiments/exp-001a/collect-metrics.sh" > "${TMP_DIR}/before.json"

set +e
RATE="${RATE}" DURATION="${DURATION}" RUN_ID="${RUN_ID}" ./scripts/measure-baseline.sh > "${TMP_DIR}/measurement.json" 2> "${TMP_DIR}/measurement.stderr"
MEASURE_EXIT=$?
set -e

END_TIMESTAMP="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
COLLECTED_AT="${END_TIMESTAMP}" "${ROOT_DIR}/experiments/exp-001a/collect-metrics.sh" > "${TMP_DIR}/after.json" || true

if (( MEASURE_EXIT != 0 )); then
  STATUS="FAIL"
  ERROR_MESSAGE="$(tr '\n' ' ' < "${TMP_DIR}/measurement.stderr" | sed 's/[[:space:]]\\+/ /g')"
  rm -f "${TMP_DIR}/measurement.json"
fi

RESULT_PATH="${RESULTS_DIR}/${RUN_ID}.json"
ANALYZE_SCRIPT="${ROOT_DIR}/experiments/exp-001a/analyze-results.py"
build_args=(
  build
  --experiment "${EXPERIMENT}"
  --run-id "${RUN_ID}"
  --rate "${RATE}"
  --duration-seconds "${DURATION}"
  --start-timestamp "${START_TIMESTAMP}"
  --end-timestamp "${END_TIMESTAMP}"
  --environment "${TMP_DIR}/environment.json"
  --before-snapshot "${TMP_DIR}/before.json"
  --after-snapshot "${TMP_DIR}/after.json"
  --status "${STATUS}"
  --output "${RESULT_PATH}"
)
if [[ -f "${TMP_DIR}/measurement.json" ]]; then
  build_args+=(--measurement "${TMP_DIR}/measurement.json")
fi
if [[ -n "${ERROR_MESSAGE}" ]]; then
  build_args+=(--error-message "${ERROR_MESSAGE}")
fi
python3 "${ANALYZE_SCRIPT}" "${build_args[@]}"

python3 "${ANALYZE_SCRIPT}" report --results-dir "${RESULTS_DIR}" --output "${REPORT_OUTPUT}"

echo "EXP-001A result: ${RESULT_PATH}"
echo "EXP-001A report: ${REPORT_OUTPUT}"
if (( MEASURE_EXIT != 0 )); then
  cat "${TMP_DIR}/measurement.stderr" >&2
  exit "${MEASURE_EXIT}"
fi
