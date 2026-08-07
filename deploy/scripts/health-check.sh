#!/usr/bin/env bash
# Report the health of the running production/staging stack: the public
# health endpoint (through the reverse proxy, exactly as a real client would
# reach it) plus each container's own health/status. Prints only status
# information - never environment values or other secrets.
#
# Usage:
#   deploy/scripts/health-check.sh [path-to-env-file]
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COMPOSE_FILE="$REPO_ROOT/docker-compose.prod.yml"
ENV_FILE="${1:-$REPO_ROOT/.env.production}"
HEALTH_PATH="/api/v1/health"

log() { printf '[health-check] %s\n' "$1"; }
fail() {
    printf '[health-check] ERROR: %s\n' "$1" >&2
    exit 1
}

[ -f "$ENV_FILE" ] || fail "Env file not found: $ENV_FILE"

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a
: "${CADDY_SITE_ADDRESS:?CADDY_SITE_ADDRESS missing from $ENV_FILE}"

COMPOSE=(docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE")
site_address="${CADDY_SITE_ADDRESS%/}"
overall_ok=1

log "Checking ${site_address}${HEALTH_PATH} ..."
if response="$(curl --silent --show-error --fail --max-time 5 -w '\n%{http_code}' "${site_address}${HEALTH_PATH}" 2>&1)"; then
    status_code="$(printf '%s' "$response" | tail -n1)"
    log "  Public health endpoint: reachable (HTTP $status_code)."
else
    log "  Public health endpoint: UNREACHABLE."
    overall_ok=0
fi

log "Container status:"
"${COMPOSE[@]}" ps --format "table {{.Name}}\t{{.Status}}"

log "Per-container health (services with a healthcheck only):"
for service in backend frontend postgres; do
    container_id="$("${COMPOSE[@]}" ps -q "$service" 2>/dev/null || true)"
    if [ -z "$container_id" ]; then
        log "  $service: not running."
        overall_ok=0
        continue
    fi
    health="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}(no healthcheck){{end}}' "$container_id" 2>/dev/null || echo "(unknown)")"
    log "  $service: $health"
    if [ "$health" = "unhealthy" ]; then
        overall_ok=0
    fi
done

if [ "$overall_ok" -eq 1 ]; then
    log "Overall: OK."
    exit 0
else
    log "Overall: PROBLEM DETECTED - see above. 'docker compose -f $COMPOSE_FILE logs <service>' for details."
    exit 1
fi
