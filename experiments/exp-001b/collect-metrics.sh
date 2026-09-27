#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${ROOT_DIR}"

COLLECTED_AT="${COLLECTED_AT:-$(date -u +"%Y-%m-%dT%H:%M:%SZ")}"
METRICS_ENDPOINT="${METRICS_ENDPOINT:-http://localhost:8888/metrics}"
TMP_METRICS_FILE="$(mktemp /tmp/exp-001b-metrics.XXXXXX)"
trap 'rm -f "${TMP_METRICS_FILE}"' EXIT

curl -fsS "${METRICS_ENDPOINT}" > "${TMP_METRICS_FILE}"
python3 - <<'PY' "${COLLECTED_AT}" "${TMP_METRICS_FILE}"
import json
import sys
from pathlib import Path
from baseline_lab.exp001a import collect_metric_snapshot

collected_at = sys.argv[1]
metrics_text = Path(sys.argv[2]).read_text(encoding="utf-8")
print(json.dumps(collect_metric_snapshot(metrics_text, collected_at=collected_at), sort_keys=True))
PY
