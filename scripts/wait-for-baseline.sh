#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

COMPOSE="${COMPOSE:-docker compose}"
WAIT_TIMEOUT="${WAIT_TIMEOUT:-120}"
WAIT_INTERVAL="${WAIT_INTERVAL:-2}"

wait_for_container() {
  local service="$1"
  local deadline=$((SECONDS + WAIT_TIMEOUT))

  while (( SECONDS < deadline )); do
    local container_id
    container_id="$(${COMPOSE} ps -q "${service}" 2>/dev/null || true)"
    if [[ -z "${container_id}" ]]; then
      sleep "${WAIT_INTERVAL}"
      continue
    fi

    local status
    status="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "${container_id}" 2>/dev/null || true)"
    case "${status}" in
      healthy|running)
        echo "${service} is ${status}"
        return 0
        ;;
      unhealthy|exited|dead)
        echo "ERROR: ${service} entered status ${status}" >&2
        ${COMPOSE} ps >&2 || true
        ${COMPOSE} logs --tail=120 "${service}" >&2 || true
        return 1
        ;;
    esac

    sleep "${WAIT_INTERVAL}"
  done

  echo "ERROR: timed out waiting for ${service}" >&2
  ${COMPOSE} ps >&2 || true
  ${COMPOSE} logs --tail=120 "${service}" >&2 || true
  return 1
}

wait_for_http() {
  local url="$1"
  local deadline=$((SECONDS + WAIT_TIMEOUT))

  while (( SECONDS < deadline )); do
    if curl -fsS "${url}" >/dev/null 2>&1; then
      echo "${url} is reachable"
      return 0
    fi
    sleep "${WAIT_INTERVAL}"
  done

  echo "ERROR: timed out waiting for ${url}" >&2
  return 1
}

wait_for_container kafka
wait_for_container otel-collector
wait_for_http "http://localhost:13133"
