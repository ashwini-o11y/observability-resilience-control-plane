#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${ROOT_DIR}"

COLLECTED_AT="${COLLECTED_AT:-$(date -u +"%Y-%m-%dT%H:%M:%SZ")}"
METRICS_ENDPOINT="${METRICS_ENDPOINT:-http://localhost:8888/metrics}"

metrics_text="$(curl -fsS "${METRICS_ENDPOINT}")"

printf '%s' "${metrics_text}" | python3 - <<'PY' "${COLLECTED_AT}"
import json
import sys

from baseline_lab.exp001a import collect_metric_snapshot

collected_at = sys.argv[1]
metrics_text = sys.stdin.read()

print(json.dumps(collect_metric_snapshot(metrics_text, collected_at=collected_at), indent=2, sort_keys=True))
PY
