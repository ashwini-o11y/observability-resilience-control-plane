#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

COLLECTOR_IMAGE="${COLLECTOR_IMAGE:-otel/opentelemetry-collector-contrib:0.111.0}"
COMPONENTS_OUTPUT="$(docker run --rm "${COLLECTOR_IMAGE}" components)"
BASELINE_CONFIG="$(mktemp)"
OPTIONAL_CONFIG="$(mktemp)"

cleanup() {
  rm -f "${BASELINE_CONFIG}" "${OPTIONAL_CONFIG}"
}
trap cleanup EXIT
chmod 644 "${BASELINE_CONFIG}" "${OPTIONAL_CONFIG}"

require_component() {
  local component_type="$1"
  local name="$2"
  if ! python3 - <<'PY' "${component_type}" "${name}" "${COMPONENTS_OUTPUT}"
import sys

component_type, name, output = sys.argv[1:]
section = None
found = False

for raw_line in output.splitlines():
    line = raw_line.rstrip()
    if line.endswith(":") and not line.startswith("    "):
        section = line[:-1]
        continue
    if section == component_type and line.strip() == f"- name: {name}":
        found = True
        break

sys.exit(0 if found else 1)
PY
  then
    echo "ERROR: ${COLLECTOR_IMAGE} does not expose ${component_type} component '${name}'" >&2
    exit 1
  fi
}

require_component receivers kafka
require_component receivers otlp
require_component processors batch
require_component processors memory_limiter
require_component exporters debug
require_component exporters file
require_component exporters otlphttp
require_component exporters splunk_hec
require_component extensions health_check

python3 -m baseline_lab.render_collector_config --output "${BASELINE_CONFIG}" >/dev/null
docker run --rm \
  -v "${BASELINE_CONFIG}:/etc/otelcol-contrib/config.yaml:ro" \
  "${COLLECTOR_IMAGE}" \
  validate --config=/etc/otelcol-contrib/config.yaml

ENABLE_DYNATRACE=true ENABLE_SPLUNK=true python3 -m baseline_lab.render_collector_config --output "${OPTIONAL_CONFIG}" >/dev/null
docker run --rm \
  -e DYNATRACE_OTLP_ENDPOINT="https://example.live.dynatrace.com/api/v2/otlp" \
  -e DYNATRACE_API_TOKEN="placeholder-token" \
  -e SPLUNK_HEC_ENDPOINT="https://splunk.example.com:8088/services/collector" \
  -e SPLUNK_HEC_TOKEN="placeholder-token" \
  -e SPLUNK_HEC_INDEX="main" \
  -v "${OPTIONAL_CONFIG}:/etc/otelcol-contrib/config.yaml:ro" \
  "${COLLECTOR_IMAGE}" \
  validate --config=/etc/otelcol-contrib/config.yaml

echo "Validated ${COLLECTOR_IMAGE} components and collector configs."
